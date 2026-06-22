import os
import time
import random
import sys
from backend.data.scraper import fetch_season_games, fetch_game_play_by_play, get_db_connection

# Target Seasons from 2017-18 through 2024-25
SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25"
]

def sleep_with_countdown(seconds: int, reason: str):
    """Sleeps for a total duration while periodically printing a status update."""
    interval = 30 # Print update every 30 seconds
    elapsed = 0
    while elapsed < seconds:
        remaining = seconds - elapsed
        mins = remaining // 60
        secs = remaining % 60
        print(f"[WAITING] {reason} - Remaining: {mins}m {secs}s", flush=True)
        sleep_time = min(interval, remaining)
        time.sleep(sleep_time)
        elapsed += sleep_time

def run_bulk_scrape():
    print("==================================================", flush=True)
    print("       ClutchNet Bulk NBA Data Ingestion          ", flush=True)
    print("==================================================", flush=True)
    print(f"Target seasons: {', '.join(SEASONS)}", flush=True)
    print("Starting process... (Pause-and-Resume supported)\n", flush=True)
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    for season_idx, season in enumerate(SEASONS):
        print(f"\n--- Season {season} ({season_idx+1}/{len(SEASONS)}) ---", flush=True)
        
        # 1. Fetch game lists for the season (cached if exists)
        try:
            games = fetch_season_games(season)
        except Exception as e:
            print(f"[ERROR] Failed to query games list for season {season}: {e}. Skipping.", flush=True)
            continue
            
        if games.empty:
            print(f"[ERROR] Could not fetch games list for season {season}. Skipping.", flush=True)
            continue
            
        total_games = len(games)
        print(f"Found {total_games} games in schedule.", flush=True)
        
        # 2. Iterate through season games
        skipped_count = 0
        scraped_count = 0
        
        # Connect to DB to check cache before API call
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for idx, row in games.iterrows():
            game_id = str(row['game_id'])
            matchup = row['matchup']
            
            # Check if game is already cached in database
            cursor.execute("SELECT 1 FROM play_by_play WHERE game_id = ? LIMIT 1", (game_id,))
            cached = cursor.fetchone()
            
            if cached:
                skipped_count += 1
                continue
                
            # If not cached, we need to fetch via API
            print(f"[{season}] Game {idx+1}/{total_games} | ID: {game_id} | {matchup}", flush=True)
            
            try:
                # fetch_game_play_by_play saves to db internally
                pbp = fetch_game_play_by_play(game_id, force_api=True)
                
                if pbp.empty:
                    consecutive_errors += 1
                    print(f"[WARN] Empty play-by-play returned for game {game_id}. Error streak: {consecutive_errors}", flush=True)
                else:
                    consecutive_errors = 0
                    scraped_count += 1
                    
            except Exception as e:
                consecutive_errors += 1
                print(f"[ERROR] Failed to fetch game {game_id}: {e}. Error streak: {consecutive_errors}", flush=True)
            
            # Stop if we hit a consecutive error block (probably IP rate limited)
            if consecutive_errors >= max_consecutive_errors:
                print("\n[CRITICAL] Hit too many consecutive API errors. stats.nba.com is likely rate-limiting our IP.", flush=True)
                # Sleep for 15 minutes (900 seconds)
                sleep_with_countdown(900, "Rate-limit block recovery cooldown")
                consecutive_errors = 0  # Reset streak
                
            # Normal rate-limiting safety sleep between API queries (2.0 seconds)
            time.sleep(2.0)
            
        conn.close()
        
        print(f"\nCompleted Season {season}:", flush=True)
        print(f"  - Scraped/Saved: {scraped_count}", flush=True)
        print(f"  - Already Cached (Skipped): {skipped_count}", flush=True)
        
        # Inter-season cooldown (wait 40 minutes = 2400 seconds)
        if season_idx < len(SEASONS) - 1:
            print("\nSeason transition: cooling down to prevent IP block...", flush=True)
            sleep_with_countdown(2400, "Inter-season cooldown break")
            
    print("\n==================================================", flush=True)
    print("          Bulk Ingestion Completed!               ", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    try:
        run_bulk_scrape()
    except KeyboardInterrupt:
        print("\nScraper interrupted by user. Saved data is safe in SQLite cache.", flush=True)
        sys.exit(0)
