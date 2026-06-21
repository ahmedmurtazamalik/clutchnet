import os
import sqlite3
import random
import time
import argparse
import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3
from nba_api.stats.static import teams

# Constants
DB_DIR = os.path.join(os.path.dirname(__file__), "raw")
DB_PATH = os.path.join(DB_DIR, "clutchnet_cache.db")

# Standard headers for requests to prevent rate limit blocks
HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive"
}

def get_db_connection() -> sqlite3.Connection:
    """Connect to SQLite database and ensure tables exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create games_list table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games_list (
            game_id TEXT PRIMARY KEY,
            season TEXT,
            game_date TEXT,
            matchup TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_abbr TEXT,
            away_team_abbr TEXT
        )
    """)
    
    # Create play_by_play table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS play_by_play (
            game_id TEXT,
            eventnum INTEGER,
            eventmsgtype INTEGER,
            eventmsgactiontype INTEGER,
            period INTEGER,
            wctimestring TEXT,
            pctimestring TEXT,
            homedescription TEXT,
            neutraldescription TEXT,
            visitordescription TEXT,
            score TEXT,
            scoremargin TEXT,
            player1_id INTEGER,
            player1_name TEXT,
            player1_team_id INTEGER,
            player2_id INTEGER,
            player2_name TEXT,
            player2_team_id INTEGER,
            player3_id INTEGER,
            player3_name TEXT,
            player3_team_id INTEGER,
            PRIMARY KEY (game_id, eventnum)
        )
    """)
    
    conn.commit()
    return conn

def fetch_season_games(season: str, max_games: Optional[int] = None) -> pd.DataFrame:
    """
    Fetch all regular season games for a given season.
    Checks SQLite cache first, then calls nba_api if missing.
    """
    conn = get_db_connection()
    query = "SELECT * FROM games_list WHERE season = ?"
    cached_df = pd.read_sql_query(query, conn, params=(season,))
    
    if len(cached_df) > 0:
        print(f"[CACHE] Loaded {len(cached_df)} games for season {season} from SQLite.")
        if max_games:
            return cached_df.head(max_games)
        return cached_df
    
    print(f"[API] Fetching games list for season {season} via nba_api...")
    try:
        # Prevent quick successive calls
        time.sleep(1.0)
        gamefinder = leaguegamefinder.LeagueGameFinder(
            season_nullable=season,
            season_type_nullable="Regular Season",
            league_id_nullable="00"  # NBA only (no G-League or WNBA)
        )
        all_games = gamefinder.get_data_frames()[0]
    except Exception as e:
        print(f"[API ERROR] Failed to fetch games from nba_api: {e}")
        conn.close()
        return pd.DataFrame()
        
    if all_games.empty:
        print("[API] No games returned for this season.")
        conn.close()
        return pd.DataFrame()

    # Parse matchups to define Home vs Away
    # Matchup example: 'BOS vs. LAL' (vs. = Home, @ = Away)
    games_processed = []
    grouped = all_games.groupby("GAME_ID")
    
    for game_id, group in grouped:
        if len(group) < 2:
            # We need both teams to resolve details
            continue
            
        row_a = group.iloc[0]
        row_b = group.iloc[1]
        
        # Determine who is home
        if "vs." in row_a["MATCHUP"]:
            home_row, away_row = row_a, row_b
        else:
            home_row, away_row = row_b, row_a
            
        games_processed.append({
            "game_id": str(game_id),
            "season": season,
            "game_date": home_row["GAME_DATE"],
            "matchup": home_row["MATCHUP"],
            "home_team_id": int(home_row["TEAM_ID"]),
            "away_team_id": int(away_row["TEAM_ID"]),
            "home_team_abbr": home_row["TEAM_ABBREVIATION"],
            "away_team_abbr": away_row["TEAM_ABBREVIATION"]
        })
        
    games_df = pd.DataFrame(games_processed)
    
    if not games_df.empty:
        cursor = conn.cursor()
        for _, row in games_df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO games_list 
                (game_id, season, game_date, matchup, home_team_id, away_team_id, home_team_abbr, away_team_abbr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["game_id"], row["season"], row["game_date"], row["matchup"],
                row["home_team_id"], row["away_team_id"], row["home_team_abbr"], row["away_team_abbr"]
            ))
        conn.commit()
        print(f"[CACHE] Saved {len(games_df)} games for season {season} to SQLite cache.")
        
    conn.close()
    if max_games:
        return games_df.head(max_games)
    return games_df

def parse_clock_v3(clock_str: str) -> str:
    if not clock_str or not isinstance(clock_str, str):
        return "00:00"
    match = re.match(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", clock_str)
    if not match:
        return "00:00"
    minutes = match.group(1) or "00"
    seconds = match.group(2) or "00"
    try:
        sec_val = float(seconds)
        if sec_val == int(sec_val):
            sec_str = f"{int(sec_val):02d}"
        else:
            sec_str = f"{sec_val:04.1f}"
    except ValueError:
        sec_str = "00"
    return f"{int(minutes):02d}:{sec_str}"

def map_v3_to_v2(df_v3: pd.DataFrame, home_team_id: int, away_team_id: int) -> pd.DataFrame:
    if df_v3.empty:
        return pd.DataFrame()
        
    action_map = {
        "period": 12,
        "Jump Ball": 10,
        "Made Shot": 1,
        "Missed Shot": 2,
        "Rebound": 4,
        "Foul": 6,
        "Turnover": 5,
        "Free Throw": 3,
        "Timeout": 9,
        "Substitution": 8,
        "Violation": 7
    }
    
    records = []
    running_home = 0
    running_away = 0
    n_rows = len(df_v3)
    
    for idx, row in df_v3.iterrows():
        action_type = row.get("actionType")
        sub_type = row.get("subType")
        
        msg_type = action_map.get(action_type, 0)
        if action_type == "period":
            if sub_type == "start":
                msg_type = 12
            elif sub_type == "end":
                msg_type = 13
                
        sc_home = row.get("scoreHome")
        sc_away = row.get("scoreAway")
        
        if sc_home and str(sc_home).strip() != "":
            running_home = int(sc_home)
        if sc_away and str(sc_away).strip() != "":
            running_away = int(sc_away)
            
        score_str = f"{running_away} - {running_home}"
        score_margin = running_home - running_away
        
        clock_str = parse_clock_v3(row.get("clock", ""))
        
        desc = row.get("description", "")
        team_id = row.get("teamId")
        
        homedescription = None
        visitordescription = None
        neutraldescription = None
        
        if team_id == home_team_id:
            homedescription = desc
        elif team_id == away_team_id:
            visitordescription = desc
        else:
            neutraldescription = desc
            
        player3_team_id = None
        if msg_type == 10:  # Jump Ball
            for j in range(idx + 1, n_rows):
                next_row = df_v3.iloc[j]
                next_act = next_row.get("actionType")
                next_team = next_row.get("teamId")
                if next_act in ["Made Shot", "Missed Shot", "Turnover", "Foul", "Timeout"] and next_team in [home_team_id, away_team_id]:
                    player3_team_id = int(next_team)
                    break
                    
        player1_id = row.get("personId")
        player1_name = row.get("playerName")
        player1_team_id = row.get("teamId")
        
        records.append({
            "game_id": str(row.get("gameId")),
            "eventnum": int(row.get("actionNumber")),
            "eventmsgtype": int(msg_type),
            "eventmsgactiontype": 0,
            "period": int(row.get("period")),
            "wctimestring": "",
            "pctimestring": clock_str,
            "homedescription": homedescription,
            "neutraldescription": neutraldescription,
            "visitordescription": visitordescription,
            "score": score_str,
            "scoremargin": str(score_margin),
            "player1_id": int(player1_id) if player1_id else None,
            "player1_name": player1_name,
            "player1_team_id": int(player1_team_id) if player1_team_id else None,
            "player2_id": None,
            "player2_name": None,
            "player2_team_id": None,
            "player3_id": None,
            "player3_name": None,
            "player3_team_id": int(player3_team_id) if player3_team_id else None
        })
        
    return pd.DataFrame(records)

def fetch_game_play_by_play(game_id: str, force_api: bool = False) -> pd.DataFrame:
    """
    Retrieve play-by-play logs for a specific game ID.
    Checks database cache first, then triggers API.
    """
    conn = get_db_connection()
    
    if not force_api:
        query = "SELECT * FROM play_by_play WHERE game_id = ? ORDER BY eventnum ASC"
        cached_df = pd.read_sql_query(query, conn, params=(game_id,))
        if len(cached_df) > 0:
            conn.close()
            return cached_df

    # Query games_list to find home_team_id and away_team_id
    cursor = conn.cursor()
    cursor.execute("SELECT home_team_id, away_team_id FROM games_list WHERE game_id = ?", (game_id,))
    res = cursor.fetchone()
    if res:
        home_team_id, away_team_id = res
    else:
        home_team_id, away_team_id = 0, 0

    print(f"[API] Fetching play-by-play data for Game {game_id} via nba_api...")
    retries = 3
    delay = 1.5
    df_v3 = pd.DataFrame()
    
    for attempt in range(retries):
        try:
            time.sleep(delay + random.uniform(0.5, 1.5))
            pbp = playbyplayv3.PlayByPlayV3(game_id=game_id)
            df_v3 = pbp.get_data_frames()[0]
            break
        except Exception as e:
            print(f"[API ERROR] Attempt {attempt+1}/{retries} failed for Game {game_id}: {e}")
            delay *= 2  # Exponential backoff
            
    if df_v3.empty:
        print(f"[API] Play-by-play data for Game {game_id} is unavailable.")
        conn.close()
        return pd.DataFrame()
        
    # Map V3 columns to standard V2 representation expected by database and preprocessor
    pbp_df = map_v3_to_v2(df_v3, home_team_id, away_team_id)
    
    # Save to Cache
    cursor = conn.cursor()
    pbp_records = pbp_df.to_dict("records")
    for rec in pbp_records:
        cursor.execute("""
            INSERT OR REPLACE INTO play_by_play 
            (game_id, eventnum, eventmsgtype, eventmsgactiontype, period, wctimestring, pctimestring,
             homedescription, neutraldescription, visitordescription, score, scoremargin,
             player1_id, player1_name, player1_team_id, player2_id, player2_name, player2_team_id,
             player3_id, player3_name, player3_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec["game_id"], rec["eventnum"], rec["eventmsgtype"], rec["eventmsgactiontype"], rec["period"],
            rec["wctimestring"], rec["pctimestring"], rec["homedescription"], rec["neutraldescription"],
            rec["visitordescription"], rec["score"], str(rec["scoremargin"]),
            rec["player1_id"], rec["player1_name"], rec["player1_team_id"],
            rec["player2_id"], rec["player2_name"], rec["player2_team_id"],
            rec["player3_id"], rec["player3_name"], rec["player3_team_id"]
        ))
    conn.commit()
    conn.close()
    
    print(f"[CACHE] Saved {len(pbp_df)} play-by-play events for Game {game_id} to database.")
    return pbp_df

def generate_synthetic_game(
    game_id: str, 
    home_team_abbr: str = "BOS", 
    away_team_abbr: str = "LAL", 
    home_team_id: int = 1610612738, 
    away_team_id: int = 1610612747
) -> pd.DataFrame:
    """
    Generates a realistic synthetic NBA play-by-play game and caches it in the database.
    Used as an immediate fallback or offline testing data generator.
    """
    print(f"[SYNTHETIC] Generating simulated game {game_id} ({away_team_abbr} @ {home_team_abbr})...")
    conn = get_db_connection()
    
    # Insert entry in games_list first
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO games_list 
        (game_id, season, game_date, matchup, home_team_id, away_team_id, home_team_abbr, away_team_abbr)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game_id, "2023-24-SYNTHETIC", "2026-06-18", f"{away_team_abbr} @ {home_team_abbr}",
        home_team_id, away_team_id, home_team_abbr, away_team_abbr
    ))
    conn.commit()
    
    events = []
    event_num = 1
    
    # Initial state
    home_score = 0
    away_score = 0
    possession_team_id = home_team_id  # Jump ball starts
    
    def add_event(msg_type: int, action_type: int, period: int, clock_str: str,
                  home_desc: str = None, visitor_desc: str = None, neutral_desc: str = None,
                  score_str: str = None, margin_str: str = None,
                  p1_id: int = None, p1_name: str = None, p1_team: int = None,
                  p2_id: int = None, p2_name: str = None, p2_team: int = None,
                  p3_id: int = None, p3_name: str = None, p3_team: int = None):
        nonlocal event_num
        events.append({
            "game_id": game_id,
            "eventnum": event_num,
            "eventmsgtype": msg_type,
            "eventmsgactiontype": action_type,
            "period": period,
            "wctimestring": "7:00 PM",
            "pctimestring": clock_str,
            "homedescription": home_desc,
            "neutraldescription": neutral_desc,
            "visitordescription": visitor_desc,
            "score": score_str,
            "scoremargin": margin_str,
            "player1_id": p1_id,
            "player1_name": p1_name,
            "player1_team_id": p1_team,
            "player2_id": p2_id,
            "player2_name": p2_name,
            "player2_team_id": p2_team,
            "player3_id": p3_id,
            "player3_name": p3_name,
            "player3_team_id": p3_team
        })
        event_num += 1

    # Simulate quarters
    for period in range(1, 5):
        period_length = 720  # 12 minutes in seconds
        current_time = period_length
        
        # Event 12: Period Start
        add_event(12, 0, period, "12:00", neutral_desc=f"Start of {period} Quarter")
        
        if period == 1:
            # Event 10: Jump Ball
            tip_winner = random.choice([home_team_id, away_team_id])
            possession_team_id = tip_winner
            winner_abbr = home_team_abbr if tip_winner == home_team_id else away_team_abbr
            add_event(
                10, 0, period, "12:00",
                neutral_desc=f"Jump Ball: Team {winner_abbr} wins possession",
                p1_id=101, p1_name="Center A", p1_team=home_team_id,
                p2_id=201, p2_name="Center B", p2_team=away_team_id,
                p3_id=102, p3_name="Guard A", p3_team=tip_winner
            )
            
        while current_time > 10:
            # Step game clock down randomly (between 8 and 24 seconds)
            time_elapsed = random.randint(8, 24)
            current_time = max(0, current_time - time_elapsed)
            
            # Format clock
            mins = current_time // 60
            secs = current_time % 60
            clock_str = f"{mins:02d}:{secs:02d}"
            
            # Decide event type
            # Possibilities: 1=Made FG, 2=Missed FG, 5=Turnover, 6=Foul, 9=Timeout
            event_choice = random.choices(
                [1, 2, 5, 6, 9],
                weights=[0.38, 0.42, 0.12, 0.06, 0.02]
            )[0]
            
            offense_team = possession_team_id
            defense_team = away_team_id if offense_team == home_team_id else home_team_id
            offense_abbr = home_team_abbr if offense_team == home_team_id else away_team_abbr
            defense_abbr = away_team_abbr if offense_team == home_team_id else home_team_abbr
            
            if event_choice == 1:
                # Made FG (2pt or 3pt)
                is_three = random.random() < 0.35
                pts = 3 if is_three else 2
                
                if offense_team == home_team_id:
                    home_score += pts
                    home_desc = f"Player H makes {pts}pt shot"
                    visitor_desc = None
                else:
                    away_score += pts
                    home_desc = None
                    visitor_desc = f"Player V makes {pts}pt shot"
                
                margin = home_score - away_score
                margin_str = "TIE" if margin == 0 else str(margin)
                score_str = f"{away_score} - {home_score}"
                
                add_event(
                    1, 1 if not is_three else 2, period, clock_str,
                    home_desc=home_desc, visitor_desc=visitor_desc,
                    score_str=score_str, margin_str=margin_str,
                    p1_id=103 if offense_team == home_team_id else 203,
                    p1_name="Scorer H" if offense_team == home_team_id else "Scorer V",
                    p1_team=offense_team
                )
                
                # Turnover possession
                possession_team_id = defense_team
                
            elif event_choice == 2:
                # Missed FG
                is_three = random.random() < 0.35
                if offense_team == home_team_id:
                    home_desc = "Player H misses shot"
                    visitor_desc = None
                else:
                    home_desc = None
                    visitor_desc = "Player V misses shot"
                    
                add_event(
                    2, 1 if not is_three else 2, period, clock_str,
                    home_desc=home_desc, visitor_desc=visitor_desc,
                    p1_id=103 if offense_team == home_team_id else 203,
                    p1_name="Scorer H" if offense_team == home_team_id else "Scorer V",
                    p1_team=offense_team
                )
                
                # Immediately follow with a rebound
                time_elapsed_reb = random.randint(1, 2)
                current_time = max(0, current_time - time_elapsed_reb)
                mins = current_time // 60
                secs = current_time % 60
                reb_clock_str = f"{mins:02d}:{secs:02d}"
                
                # Rebound type: 70% Defensive, 30% Offensive
                is_defensive = random.random() < 0.70
                reb_winner = defense_team if is_defensive else offense_team
                reb_winner_abbr = defense_abbr if is_defensive else offense_abbr
                
                p1_id = 104 if reb_winner == home_team_id else 204
                p1_name = "Big H" if reb_winner == home_team_id else "Big V"
                
                reb_desc = f"{p1_name} Rebound"
                h_desc = reb_desc if reb_winner == home_team_id else None
                v_desc = reb_desc if reb_winner == away_team_id else None
                
                add_event(
                    4, 0, period, reb_clock_str,
                    home_desc=h_desc, visitor_desc=v_desc,
                    p1_id=p1_id, p1_name=p1_name, p1_team=reb_winner
                )
                
                possession_team_id = reb_winner
                
            elif event_choice == 5:
                # Turnover
                is_steal = random.random() < 0.60
                t_desc = "Player commits turnover"
                h_desc = t_desc if offense_team == home_team_id else None
                v_desc = t_desc if offense_team == away_team_id else None
                
                steal_desc = "Player steals ball"
                steal_h_desc = steal_desc if defense_team == home_team_id else None
                steal_v_desc = steal_desc if defense_team == away_team_id else None
                
                # Event 5: Turnover
                add_event(
                    5, 1, period, clock_str,
                    home_desc=h_desc or steal_h_desc, visitor_desc=v_desc or steal_v_desc,
                    p1_id=105 if offense_team == home_team_id else 205,
                    p1_name="Turnover H" if offense_team == home_team_id else "Turnover V",
                    p1_team=offense_team,
                    p2_id=102 if defense_team == home_team_id else 202 if is_steal else None,
                    p2_name="Stealer H" if defense_team == home_team_id else "Stealer V" if is_steal else None,
                    p2_team=defense_team if is_steal else None
                )
                
                possession_team_id = defense_team
                
            elif event_choice == 6:
                # Foul
                is_shooting_foul = random.random() < 0.50
                f_desc = "Defensive foul"
                h_desc = f_desc if defense_team == home_team_id else None
                v_desc = f_desc if defense_team == away_team_id else None
                
                add_event(
                    6, 1, period, clock_str,
                    home_desc=h_desc, visitor_desc=v_desc,
                    p1_id=106 if defense_team == home_team_id else 206,
                    p1_name="Defender H" if defense_team == home_team_id else "Defender V",
                    p1_team=defense_team
                )
                
                if is_shooting_foul:
                    # Shoot 2 Free Throws
                    for ft_num in range(1, 3):
                        time_elapsed_ft = random.randint(1, 2)
                        current_time = max(0, current_time - time_elapsed_ft)
                        mins = current_time // 60
                        secs = current_time % 60
                        ft_clock_str = f"{mins:02d}:{secs:02d}"
                        
                        # 75% free throw success
                        made_ft = random.random() < 0.75
                        
                        if made_ft:
                            if offense_team == home_team_id:
                                home_score += 1
                            else:
                                away_score += 1
                                
                            margin = home_score - away_score
                            margin_str = "TIE" if margin == 0 else str(margin)
                            score_str = f"{away_score} - {home_score}"
                            
                            ft_desc = f"Player makes Free Throw {ft_num} of 2"
                            ft_h = ft_desc if offense_team == home_team_id else None
                            ft_v = ft_desc if offense_team == away_team_id else None
                            
                            add_event(
                                3, 10 + ft_num, period, ft_clock_str,
                                home_desc=ft_h, visitor_desc=ft_v,
                                score_str=score_str, margin_str=margin_str,
                                p1_id=103 if offense_team == home_team_id else 203,
                                p1_name="Scorer H" if offense_team == home_team_id else "Scorer V",
                                p1_team=offense_team
                            )
                        else:
                            # Missed FT
                            ft_desc = f"Player misses Free Throw {ft_num} of 2"
                            ft_h = ft_desc if offense_team == home_team_id else None
                            ft_v = ft_desc if offense_team == away_team_id else None
                            
                            add_event(
                                3, 10 + ft_num, period, ft_clock_str,
                                home_desc=ft_h, visitor_desc=ft_v,
                                p1_id=103 if offense_team == home_team_id else 203,
                                p1_name="Scorer H" if offense_team == home_team_id else "Scorer V",
                                p1_team=offense_team
                            )
                            
                            if ft_num == 2:
                                # Rebound sequence on missed final FT
                                is_defensive = random.random() < 0.85
                                reb_winner = defense_team if is_defensive else offense_team
                                p1_id = 104 if reb_winner == home_team_id else 204
                                p1_name = "Big H" if reb_winner == home_team_id else "Big V"
                                
                                reb_desc = f"{p1_name} Rebound"
                                h_desc = reb_desc if reb_winner == home_team_id else None
                                v_desc = reb_desc if reb_winner == away_team_id else None
                                
                                add_event(
                                    4, 0, period, ft_clock_str,
                                    home_desc=h_desc, visitor_desc=v_desc,
                                    p1_id=p1_id, p1_name=p1_name, p1_team=reb_winner
                                )
                                possession_team_id = reb_winner
                    
                    # Possession change after made final FT
                    if made_ft:
                        possession_team_id = defense_team
                        
            elif event_choice == 9:
                # Timeout
                t_desc = f"Team Timeout"
                h_desc = t_desc if offense_team == home_team_id else None
                v_desc = t_desc if offense_team == away_team_id else None
                add_event(
                    9, 0, period, clock_str,
                    home_desc=h_desc, visitor_desc=v_desc,
                    p1_id=offense_team, p1_team=offense_team
                )
                
        # Event 13: Period End
        add_event(13, 0, period, "00:00", neutral_desc=f"End of {period} Quarter")

    # Save to SQLite play_by_play
    cursor = conn.cursor()
    for rec in events:
        cursor.execute("""
            INSERT OR REPLACE INTO play_by_play 
            (game_id, eventnum, eventmsgtype, eventmsgactiontype, period, wctimestring, pctimestring,
             homedescription, neutraldescription, visitordescription, score, scoremargin,
             player1_id, player1_name, player1_team_id, player2_id, player2_name, player2_team_id,
             player3_id, player3_name, player3_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec["game_id"], rec["eventnum"], rec["eventmsgtype"], rec["eventmsgactiontype"], rec["period"],
            rec["wctimestring"], rec["pctimestring"], rec["homedescription"], rec["neutraldescription"],
            rec["visitordescription"], rec["score"], str(rec["scoremargin"]),
            rec["player1_id"], rec["player1_name"], rec["player1_team_id"],
            rec["player2_id"], rec["player2_name"], rec["player2_team_id"],
            rec["player3_id"], rec["player3_name"], rec["player3_team_id"]
        ))
    conn.commit()
    conn.close()
    
    print(f"[SYNTHETIC] Saved {len(events)} synthetic play-by-play events for Game {game_id} to database.")
    return pd.DataFrame(events)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClutchNet NBA Stats Ingestion CLI")
    parser.add_argument("--season", type=str, default="2023-24", help="Season to fetch (e.g. 2023-24)")
    parser.add_argument("--max-games", type=int, default=5, help="Limit number of games to scrape for testing")
    parser.add_argument("--synthetic", action="store_true", help="Generate a mock/synthetic game instead of calling API")
    parser.add_argument("--game-id", type=str, default="9990000001", help="Game ID for synthetic generator or manual fetch")
    args = parser.parse_args()
    
    if args.synthetic:
        generate_synthetic_game(args.game_id)
    else:
        print(f"Ingesting season {args.season} (Limit: {args.max_games} games)...")
        games = fetch_season_games(args.season, max_games=args.max_games)
        if not games.empty:
            for idx, row in games.iterrows():
                print(f"\n({idx+1}/{len(games)}) Processing Game ID: {row['game_id']} - {row['matchup']}")
                fetch_game_play_by_play(row['game_id'])
                # Rate limit safety sleep
                time.sleep(2.0)
        print("\nIngestion complete.")
