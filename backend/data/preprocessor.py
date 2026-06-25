import os
import sqlite3
import pandas as pd
import numpy as np
import json
from typing import Tuple, Dict, Any

# Default Elo if team abbreviation not found
DEFAULT_ELO = 1500

def parse_time_to_seconds(pctimestring: str) -> float:
    """Converts a PCTIMESTRING (e.g. '11:58', '00:04.5') to remaining seconds."""
    if not pctimestring or not isinstance(pctimestring, str):
        return 0.0
    try:
        parts = pctimestring.split(":")
        if len(parts) != 2:
            return 0.0
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60.0 + seconds
    except Exception:
        return 0.0

def preprocess_game(
    game_id: str, 
    pbp_df: pd.DataFrame, 
    home_team_id: int, 
    away_team_id: int,
    home_team_abbr: str,
    away_team_abbr: str,
    home_elo: float = DEFAULT_ELO,
    away_elo: float = DEFAULT_ELO
) -> pd.DataFrame:
    """
    Evaluates play-by-play events chronologically to engineer snapshot features.
    """
    if pbp_df.empty:
        return pd.DataFrame()

    # Ensure chronological order
    pbp_df = pbp_df.sort_values(by="eventnum").copy()

    # Output features storage
    processed_events = []

    # Running State Variables
    home_score = 0
    away_score = 0
    possession = 0  # 1: Home, -1: Away, 0: Neutral
    home_timeouts_remaining = 7
    away_timeouts_remaining = 7
    
    # Fouls track per period: reset on start of period
    home_fouls = 0
    away_fouls = 0
    
    # Help track rebound states
    last_shot_shooter_team_id = None

    # Running Momentum & Context variables
    largest_lead = 0.0
    last_non_tie_leader = 0  # 0: tie, 1: home, -1: away
    lead_changes = 0.0
    history = []  # list of (elapsed_time, home_score, away_score)

    def clean_desc(val: Any) -> str:
        if val is None or pd.isna(val):
            return ""
        return str(val).strip()

    for _, row in pbp_df.iterrows():
        event_type = int(row["eventmsgtype"])
        period = int(row["period"])
        
        # Extract and clean descriptions
        h_desc = clean_desc(row["homedescription"])
        v_desc = clean_desc(row["visitordescription"])
        n_desc = clean_desc(row["neutraldescription"])
        desc = (h_desc or v_desc or "").upper()
        
        # Reset fouls on new period start
        if event_type == 12:  # Start Period
            home_fouls = 0
            away_fouls = 0
            possession = 0
            last_shot_shooter_team_id = None

        # Parse Time Remaining in Period
        seconds_remaining_in_period = parse_time_to_seconds(row["pctimestring"])
        
        # Parse Time Remaining in Game (Regulation is 4 periods of 720 seconds)
        if period <= 4:
            seconds_remaining_in_game = max(0.0, (4 - period) * 720.0) + seconds_remaining_in_period
            elapsed_time = (period - 1) * 720.0 + (720.0 - seconds_remaining_in_period)
        else:
            # Overtime (5 minutes = 300 seconds)
            seconds_remaining_in_game = seconds_remaining_in_period
            elapsed_time = 2880.0 + (period - 5) * 300.0 + (300.0 - seconds_remaining_in_period)

        # Score parsing and forward fill
        score_str = row["score"]
        if score_str and isinstance(score_str, str) and "-" in score_str:
            try:
                # Format is typically "VisitorScore - HomeScore"
                parts = score_str.split(" - ")
                away_score = int(parts[0].strip())
                home_score = int(parts[1].strip())
            except ValueError:
                pass
        
        score_margin = home_score - away_score

        # Possession State Tracker Machine
        if event_type == 1:  # Made Field Goal
            p1_team = row["player1_team_id"]
            # The scoring team was on offense; possession shifts to the defending team
            if p1_team == home_team_id:
                possession = -1
            elif p1_team == away_team_id:
                possession = 1
            else:
                # Fallback: score-based guess
                possession = -1 if possession == 1 else 1
            last_shot_shooter_team_id = None

        elif event_type == 2:  # Missed Field Goal
            # Record who shot the ball for rebound tracking
            last_shot_shooter_team_id = row["player1_team_id"]
            # Possession is now contested
            possession = 0

        elif event_type == 4:  # Rebound
            p1_team = row["player1_team_id"]
            if pd.notna(p1_team) and p1_team:
                p1_team = int(p1_team)
                if p1_team == last_shot_shooter_team_id:
                    # Offensive rebound -> possession stays with the shooter
                    possession = 1 if p1_team == home_team_id else -1
                else:
                    # Defensive rebound -> possession goes to the rebounding team
                    possession = 1 if p1_team == home_team_id else -1
            else:
                # Team rebound fallback (parse descriptions)
                if h_desc and "REBOUND" in h_desc.upper():
                    possession = 1
                elif v_desc and "REBOUND" in v_desc.upper():
                    possession = -1
            last_shot_shooter_team_id = None

        elif event_type == 5:  # Turnover
            p1_team = row["player1_team_id"]
            # Ball is lost -> possession shifts to other team
            if p1_team == home_team_id:
                possession = -1
            elif p1_team == away_team_id:
                possession = 1
            else:
                possession = -1 if possession == 1 else 1
            last_shot_shooter_team_id = None

        elif event_type == 10:  # Jump Ball
            p3_team = row["player3_team_id"]
            if p3_team == home_team_id:
                possession = 1
            elif p3_team == away_team_id:
                possession = -1
            last_shot_shooter_team_id = None

        elif event_type == 3:  # Free Throw
            p1_team = row["player1_team_id"]
            
            # Check if it was made
            # Score updates are handled by the score parsing block above,
            # but we need to track possession on the final free throw of a trip.
            is_made = "MAKE" in desc or "PTS" in desc
            
            # Check if this is the last free throw of a sequence
            is_last_ft = "1 OF 1" in desc or "2 OF 2" in desc or "3 OF 3" in desc or "TECHNICAL" in desc
            
            if is_last_ft:
                if is_made:
                    # If made, defending team gets the ball
                    if p1_team == home_team_id:
                        possession = -1
                    elif p1_team == away_team_id:
                        possession = 1
                else:
                    # Contested state for rebound
                    possession = 0
                last_shot_shooter_team_id = p1_team

        # Resource tracking: Timeouts
        elif event_type == 9:  # Timeout
            if h_desc and "TIMEOUT" in h_desc.upper():
                home_timeouts_remaining = max(0, home_timeouts_remaining - 1)
                possession = 1
            elif v_desc and "TIMEOUT" in v_desc.upper():
                away_timeouts_remaining = max(0, away_timeouts_remaining - 1)
                possession = -1

        # Resource tracking: Fouls
        elif event_type == 6:  # Foul
            p1_team = row["player1_team_id"]
            
            # Determine if this foul counts towards the team penalty.
            # Offensive/player-control fouls do NOT count.
            is_offensive = "OFF.FOUL" in desc or "OFFENSIVE" in desc or "CHARGE" in desc or "PLAYER CONTROL" in desc
            
            if not is_offensive:
                if p1_team == home_team_id:
                    home_fouls = min(5, home_fouls + 1)
                elif p1_team == away_team_id:
                    away_fouls = min(5, away_fouls + 1)

        # Derived Context features
        is_overtime = 1 if period > 4 else 0
        is_clutch = 1 if (seconds_remaining_in_game <= 300.0 and abs(score_margin) <= 5.0) else 0
        largest_lead = max(largest_lead, abs(score_margin))

        if score_margin > 0:
            current_leader = 1
        elif score_margin < 0:
            current_leader = -1
        else:
            current_leader = 0

        if current_leader != 0:
            if last_non_tie_leader != 0 and current_leader != last_non_tie_leader:
                lead_changes += 1
            last_non_tie_leader = current_leader

        # Momentum lookback (last 180 seconds of elapsed game time)
        lookback_idx = len(history) - 1
        while lookback_idx >= 0 and (elapsed_time - history[lookback_idx][0]) <= 180.0:
            lookback_idx -= 1

        if lookback_idx >= 0:
            prev_home_score = history[lookback_idx][1]
            prev_away_score = history[lookback_idx][2]
        else:
            prev_home_score = 0
            prev_away_score = 0

        home_pts_last_3_min = home_score - prev_home_score
        away_pts_last_3_min = away_score - prev_away_score

        history.append((elapsed_time, home_score, away_score))

        # Append computed features at this snapshot
        processed_events.append({
            "game_id": game_id,
            "eventnum": int(row["eventnum"]),
            "period": period,
            "seconds_remaining_in_period": seconds_remaining_in_period,
            "seconds_remaining_in_game": seconds_remaining_in_game,
            "home_score": home_score,
            "away_score": away_score,
            "score_margin": float(score_margin),
            "possession": possession,
            "home_timeouts_remaining": home_timeouts_remaining,
            "away_timeouts_remaining": away_timeouts_remaining,
            "home_fouls": home_fouls,
            "away_fouls": away_fouls,
            "home_pregame_rating": float(home_elo),
            "away_pregame_rating": float(away_elo),
            "is_overtime": int(is_overtime),
            "is_clutch": int(is_clutch),
            "largest_lead": float(largest_lead),
            "lead_changes": float(lead_changes),
            "home_pts_last_3_min": float(home_pts_last_3_min),
            "away_pts_last_3_min": float(away_pts_last_3_min),
            "description": h_desc or v_desc or n_desc or ""
        })

    # Return as a structured DataFrame
    return pd.DataFrame(processed_events)

def get_game_winner(pbp_processed_df: pd.DataFrame) -> int:
    """
    Returns 1 if home team won, 0 if away team won.
    Evaluates final score of the processed play sequence.
    """
    if pbp_processed_df.empty:
        return 0
    final_row = pbp_processed_df.iloc[-1]
    return 1 if final_row["home_score"] > final_row["away_score"] else 0

def preprocess_all_cached_games(processed_dir: str = "processed") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Queries all games cached in SQLite, processes them chronologically to compute
    dynamic rolling Elo ratings, engineers advanced features, and splits datasets
    temporally into train/validation/test folders.
    """
    db_path = os.path.join(os.path.dirname(__file__), "raw", "clutchnet_cache.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found at {db_path}. Run scraper first.")
        
    conn = sqlite3.connect(db_path)
    
    # Load all unique game listings
    games_list_df = pd.read_sql_query("SELECT * FROM games_list", conn)
    print(f"[PREPROCESSOR] Found {len(games_list_df)} games in SQLite cache.")
    
    # Filter out synthetic games from train/val/test splits
    real_games_list_df = games_list_df[games_list_df["season"] != "2023-24-SYNTHETIC"].copy()
    
    # Sort chronologically by game_date and game_id
    real_games_list_df = real_games_list_df.sort_values(by=["game_date", "game_id"]).copy()
    print(f"[PREPROCESSOR] Sorted {len(real_games_list_df)} real games chronologically.")
    
    current_elos = {}
    last_season = None
    all_game_dfs = []
    
    # Compute rolling Elo ratings chronologically
    for idx, game in real_games_list_df.iterrows():
        game_id = game["game_id"]
        season = game["season"]
        home_team = game["home_team_abbr"]
        away_team = game["away_team_abbr"]
        
        # FiveThirtyEight season-to-season Elo regression (regression towards the mean 1500)
        if last_season is not None and last_season != season:
            for team in current_elos:
                current_elos[team] = 0.75 * current_elos[team] + 0.25 * 1500.0
        last_season = season
        
        # Get pregame Elos
        home_elo = current_elos.get(home_team, DEFAULT_ELO)
        away_elo = current_elos.get(away_team, DEFAULT_ELO)
        
        # Fetch raw play-by-play events
        pbp_raw = pd.read_sql_query(
            "SELECT * FROM play_by_play WHERE game_id = ? ORDER BY eventnum ASC",
            conn, params=(game_id,)
        )
        
        # Process events with pregame Elos
        pbp_processed = preprocess_game(
            game_id=game_id,
            pbp_df=pbp_raw,
            home_team_id=int(game["home_team_id"]),
            away_team_id=int(game["away_team_id"]),
            home_team_abbr=home_team,
            away_team_abbr=away_team,
            home_elo=home_elo,
            away_elo=away_elo
        )
        
        if pbp_processed.empty:
            continue
            
        # Determine label (who won the game)
        winner_label = get_game_winner(pbp_processed)
        pbp_processed["label"] = winner_label
        
        all_game_dfs.append(pbp_processed)
        
        # Update rolling Elo ratings
        # HCA = 100 points, K-factor = 20
        hca = 100.0
        expected_home = 1.0 / (1.0 + 10.0 ** ((away_elo - (home_elo + hca)) / 400.0))
        k = 20.0
        shift = k * (winner_label - expected_home)
        
        current_elos[home_team] = home_elo + shift
        current_elos[away_team] = away_elo - shift
        
    conn.close()
    
    if not all_game_dfs:
        print("[PREPROCESSOR] No games processed successfully.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    # Save the final Elo ratings to latest_elos.json for low-latency live serving
    latest_elos_path = os.path.join(os.path.dirname(__file__), "..", "model", "latest_elos.json")
    with open(latest_elos_path, "w") as f:
        json.dump(current_elos, f, indent=4)
    print(f"[PREPROCESSOR] Saved latest Elo ratings to {latest_elos_path}")
    
    # Split chronologically by season boundaries:
    # Train: 2014-15 through 2021-22 (~8 seasons)
    # Val:   2022-23 (1 season)
    # Test:  2023-24 and 2024-25 (2 seasons)
    train_seasons = {"2014-15", "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22"}
    val_seasons = {"2022-23"}
    test_seasons = {"2023-24", "2024-25"}
    
    game_id_to_season = real_games_list_df.set_index("game_id")["season"].to_dict()
    
    train_list = []
    val_list = []
    test_list = []
    
    for df in all_game_dfs:
        g_id = df["game_id"].iloc[0]
        g_season = game_id_to_season.get(g_id)
        if g_season in train_seasons:
            train_list.append(df)
        elif g_season in val_seasons:
            val_list.append(df)
        elif g_season in test_seasons:
            test_list.append(df)
            
    train_df = pd.concat(train_list, ignore_index=True) if train_list else pd.DataFrame()
    val_df = pd.concat(val_list, ignore_index=True) if val_list else pd.DataFrame()
    test_df = pd.concat(test_list, ignore_index=True) if test_list else pd.DataFrame()
    
    # Save datasets
    output_path = os.path.join(os.path.dirname(__file__), processed_dir)
    os.makedirs(output_path, exist_ok=True)
    
    if not train_df.empty:
        train_df.to_csv(os.path.join(output_path, "train_features.csv"), index=False)
    if not val_df.empty:
        val_df.to_csv(os.path.join(output_path, "val_features.csv"), index=False)
    if not test_df.empty:
        test_df.to_csv(os.path.join(output_path, "test_features.csv"), index=False)
        
    print(f"[PREPROCESSOR] Datasets created in '{output_path}':")
    print(f"  - Train: {len(train_df)} rows ({len(train_list)} games)")
    print(f"  - Val:   {len(val_df)} rows ({len(val_list)} games)")
    print(f"  - Test:  {len(test_df)} rows ({len(test_list)} games)")
    
    return train_df, val_df, test_df

if __name__ == "__main__":
    print("Running preprocessing on SQLite cached games...")
    preprocess_all_cached_games()
