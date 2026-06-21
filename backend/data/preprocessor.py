import os
import sqlite3
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

# Static Elo ratings for the 2023-24 season (as a baseline prior)
TEAM_ELOS = {
    "BOS": 1650, "DEN": 1610, "OKC": 1600, "MIN": 1580, "LAC": 1560,
    "MIL": 1550, "NYK": 1560, "PHI": 1540, "DAL": 1570, "CLE": 1530,
    "IND": 1520, "PHX": 1520, "NOP": 1510, "LAL": 1510, "MIA": 1500,
    "SAC": 1500, "GSW": 1510, "HOU": 1480, "CHI": 1460, "ATL": 1450,
    "UTA": 1420, "BKN": 1410, "TOR": 1390, "MEM": 1370, "SAS": 1350,
    "POR": 1330, "CHA": 1310, "CHO": 1310, "WAS": 1290, "DET": 1270
}

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
    away_team_abbr: str
) -> pd.DataFrame:
    """
    Evaluates play-by-play events chronologically to engineer snapshot features.
    """
    if pbp_df.empty:
        return pd.DataFrame()

    # Ensure chronological order
    pbp_df = pbp_df.sort_values(by="eventnum").copy()

    # Pre-game Elos
    home_elo = TEAM_ELOS.get(home_team_abbr, DEFAULT_ELO)
    away_elo = TEAM_ELOS.get(away_team_abbr, DEFAULT_ELO)

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
        else:
            # Overtime (5 minutes = 300 seconds)
            seconds_remaining_in_game = 0.0  # Regulation is over

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
    Queries all games cached in SQLite, processes them, adds binary outcomes,
    and splits datasets into train/validation/test folders.
    """
    db_path = os.path.join(os.path.dirname(__file__), "raw", "clutchnet_cache.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found at {db_path}. Run scraper first.")
        
    conn = sqlite3.connect(db_path)
    
    # Load all unique game listings
    games_list_df = pd.read_sql_query("SELECT * FROM games_list", conn)
    print(f"[PREPROCESSOR] Found {len(games_list_df)} games in SQLite cache.")
    
    all_game_dfs = []
    
    for _, game in games_list_df.iterrows():
        game_id = game["game_id"]
        # Fetch raw PBP
        pbp_raw = pd.read_sql_query(
            "SELECT * FROM play_by_play WHERE game_id = ? ORDER BY eventnum ASC",
            conn, params=(game_id,)
        )
        
        # Process events
        pbp_processed = preprocess_game(
            game_id=game_id,
            pbp_df=pbp_raw,
            home_team_id=int(game["home_team_id"]),
            away_team_id=int(game["away_team_id"]),
            home_team_abbr=game["home_team_abbr"],
            away_team_abbr=game["away_team_abbr"]
        )
        
        if pbp_processed.empty:
            continue
            
        # Determine label (who won the game)
        winner_label = get_game_winner(pbp_processed)
        pbp_processed["label"] = winner_label
        
        all_game_dfs.append(pbp_processed)
        
    conn.close()
    
    if not all_game_dfs:
        print("[PREPROCESSOR] No games processed successfully.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    # Group splits by Game ID to avoid sequence leakages
    game_ids = list(games_list_df["game_id"].unique())
    # Shuffle game ids for random splits
    random_state = np.random.RandomState(42)
    random_state.shuffle(game_ids)
    
    n_games = len(game_ids)
    train_end = int(n_games * 0.8)
    val_end = int(n_games * 0.9)
    
    train_ids = set(game_ids[:train_end])
    val_ids = set(game_ids[train_end:val_end])
    test_ids = set(game_ids[val_end:])
    
    train_list = [df for df in all_game_dfs if df["game_id"].iloc[0] in train_ids]
    val_list = [df for df in all_game_dfs if df["game_id"].iloc[0] in val_ids]
    test_list = [df for df in all_game_dfs if df["game_id"].iloc[0] in test_ids]
    
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
