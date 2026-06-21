import os
import time
import random
import sys
from backend.data.scraper import fetch_season_games, fetch_game_play_by_play, get_db_connection

# 10 NBA Seasons to scrape
SEASONS = [
    "2014-15", "2015-16", "2016-17", "2017-18", "2018-19",
    "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"
]

def run_bulk_scrape():
    print("==================================================")
    print("       ClutchNet Bulk NBA Data Ingestion          ")
    print("==================================================")
    print(f"Target seasons: {', '.join(SEASONS)}")
    print("Starting process... (Pause-and-Resume supported)\n")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    for season_idx, season in enumerate(SEASONS):
        print(f"\n--- Season {season} ({season_idx+1}/{len(SEASONS)}) ---")
        
        # 1. Fetch game lists for the season (cached if exists)
        games = fetch_season_games(season)
        if games.empty:
            print(f"[ERROR] Could not fetch games list for season {season}. Skipping.")
            continue
            
        total_games = len(games)
        print(f"Found {total_games} games in schedule.")
        
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
            print(f"[{season}] Game {idx+1}/{total_games} | ID: {game_id} | {matchup}")
            
            try:
                # fetch_game_play_by_play saves to db internally
                pbp = fetch_game_play_by_play(game_id, force_api=True)
                
                if pbp.empty:
                    consecutive_errors += 1
                    print(f"[WARN] Empty play-by-play returned for game {game_id}. Error streak: {consecutive_errors}")
                else:
                    consecutive_errors = 0
                    scraped_count += 1
                    
            except Exception as e:
                consecutive_errors += 1
                print(f"[ERROR] Failed to fetch game {game_id}: {e}. Error streak: {consecutive_errors}")
            
            # Stop if we hit a consecutive error block (probably IP rate limited)
            if consecutive_errors >= max_consecutive_errors:
                print("\n[CRITICAL] Hit too many consecutive API errors. stats.nba.com is likely rate-limiting our IP.")
                print("Entering a 15-minute cool-down period to let the limit reset...")
                time.sleep(900)  # Sleep for 15 minutes
                consecutive_errors = 0  # Reset streak
                
            # Normal rate-limiting safety sleep between API queries (3-5 seconds)
            time.sleep(random.uniform(3.0, 5.0))
            
        conn.close()
        
        print(f"\nCompleted Season {season}:")
        print(f"  - Scraped/Saved: {scraped_count}")
        print(f"  - Already Cached (Skipped): {skipped_count}")
        
        # Inter-season cooldown (wait 2 minutes to let the connection cool down)
        if season_idx < len(SEASONS) - 1:
            print("\nSeason transition: cooling down for 2 minutes...")
            time.sleep(120)
            
    print("\n==================================================")
    print("          Bulk Ingestion Completed!               ")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_bulk_scrape()
    except KeyboardInterrupt:
        print("\nScraper interrupted by user. Saved data is safe in SQLite cache.")
        sys.exit(0)
