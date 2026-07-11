import asyncio
import os
import json
import sqlite3
from typing import Optional, List, Dict, Any
import pandas as pd
from backend.model.predictor import Predictor
from backend.data.preprocessor import preprocess_game
from backend.ws_manager import ConnectionManager

# Path to local SQLite database cache
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "raw", "clutchnet_cache.db")

class ReplaySimulator:
    def __init__(self, predictor: Predictor, ws_manager: ConnectionManager):
        self.predictor = predictor
        self.ws_manager = ws_manager
        
        # State variables
        self.game_id: Optional[str] = None
        self.events: List[Dict[str, Any]] = []
        self.current_idx: int = 0
        self.is_running: bool = False
        self.speed_multiplier: float = 10.0  # Default 10x speed replay
        self.simulation_task: Optional[asyncio.Task] = None
        
        # Load pregame Elos if cached
        elos_path = os.path.join(os.path.dirname(__file__), "model", "latest_elos.json")
        if os.path.exists(elos_path):
            try:
                with open(elos_path, "r") as f:
                    self.elos = json.load(f)
            except Exception as e:
                print(f"[SIMULATOR] Warning: Failed to load latest_elos.json: {e}")
                self.elos = {}
        else:
            self.elos = {}

    def get_game_details(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Queries the cached games list to get team IDs and abbreviations."""
        if not os.path.exists(DB_PATH):
            print(f"[SIMULATOR] Database not found at {DB_PATH}")
            return None
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, season, game_date, matchup, home_team_id, away_team_id, home_team_abbr, away_team_abbr
            FROM games_list WHERE game_id = ?
        """, (game_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
            
        home_team_id = row[4]
        away_team_id = row[5]
        
        # Fallback dynamic team ID extraction if they are None in games_list
        if home_team_id is None:
            cursor.execute("""
                SELECT DISTINCT player1_team_id 
                FROM play_by_play 
                WHERE game_id = ? AND homedescription IS NOT NULL AND player1_team_id IS NOT NULL 
                LIMIT 1
            """, (game_id,))
            home_row = cursor.fetchone()
            if home_row:
                home_team_id = home_row[0]
                
        if away_team_id is None:
            cursor.execute("""
                SELECT DISTINCT player1_team_id 
                FROM play_by_play 
                WHERE game_id = ? AND visitordescription IS NOT NULL AND player1_team_id IS NOT NULL 
                LIMIT 1
            """, (game_id,))
            away_row = cursor.fetchone()
            if away_row:
                away_team_id = away_row[0]
                
        conn.close()
        
        return {
            "game_id": row[0],
            "season": row[1],
            "game_date": row[2],
            "matchup": row[3],
            "home_team_id": int(home_team_id) if home_team_id is not None else None,
            "away_team_id": int(away_team_id) if away_team_id is not None else None,
            "home_team_abbr": row[6],
            "away_team_abbr": row[7]
        }

    def load_game(self, game_id: str) -> bool:
        """
        Loads the play-by-play events from SQLite database,
        runs them through feature preprocessing and PyTorch predictor inference.
        """
        print(f"[SIMULATOR] Loading game {game_id}...")
        
        # Stop any active simulation task first
        self.stop()
        
        # Query game metadata
        game_details = self.get_game_details(game_id)
        if not game_details:
            print(f"[SIMULATOR] Game {game_id} metadata not found in SQLite cache.")
            return False
            
        # Query play-by-play records
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM play_by_play WHERE game_id = ? ORDER BY eventnum ASC"
        pbp_df = pd.read_sql_query(query, conn, params=(game_id,))
        conn.close()
        
        # Fallback: if play-by-play records are missing, dynamically scrape them from the NBA API
        if pbp_df.empty:
            print(f"[SIMULATOR] Play-by-play records for game {game_id} are empty. Fetching dynamically from NBA API...")
            try:
                from backend.data.scraper import fetch_game_play_by_play
                pbp_df = fetch_game_play_by_play(game_id, force_api=True)
            except Exception as e:
                print(f"[SIMULATOR] Dynamic scraping failed for game {game_id}: {e}")
                return False
            
        if pbp_df.empty:
            print(f"[SIMULATOR] Play-by-play records for game {game_id} are still empty or missing after API call.")
            return False
            
        home_elo = self.elos.get(game_details["home_team_abbr"], 1500.0)
        away_elo = self.elos.get(game_details["away_team_abbr"], 1500.0)
        
        # Process events to create snapshots
        try:
            processed_df = preprocess_game(
                game_id=game_id,
                pbp_df=pbp_df,
                home_team_id=game_details["home_team_id"],
                away_team_id=game_details["away_team_id"],
                home_team_abbr=game_details["home_team_abbr"],
                away_team_abbr=game_details["away_team_abbr"],
                home_elo=home_elo,
                away_elo=away_elo
            )
        except Exception as e:
            print(f"[SIMULATOR] Preprocessing failed for game {game_id}: {e}")
            return False
            
        if processed_df.empty:
            print(f"[SIMULATOR] Preprocessed features are empty.")
            return False
            
        # Convert processed DataFrame to dict list
        self.events = processed_df.to_dict("records")
        self.game_id = game_id
        self.current_idx = 0
        
        # Precompute win probabilities and deltas for the entire play sequence
        print(f"[SIMULATOR] Pre-calculating model win probabilities for {len(self.events)} events...")
        for idx, event in enumerate(self.events):
            try:
                # Add basic team identifiers to the event payload for the frontend
                event["home_team_abbr"] = game_details["home_team_abbr"]
                event["away_team_abbr"] = game_details["away_team_abbr"]
                event["matchup"] = game_details["matchup"]
                
                # Perform model prediction
                prob = self.predictor.predict(event)
                event["win_probability"] = prob
                
                # Calculate play delta
                if idx == 0:
                    event["play_delta"] = 0.0
                else:
                    event["play_delta"] = prob - self.events[idx - 1]["win_probability"]
            except Exception as e:
                print(f"[SIMULATOR] Inference failed at event index {idx}: {e}")
                # Fallback parameters
                event["win_probability"] = 0.5
                event["play_delta"] = 0.0
                
        print(f"[SIMULATOR] Loaded and initialized game {game_id} successfully.")
        return True

    def start(self, game_id: str) -> bool:
        """Loads and starts simulation from the beginning."""
        if self.load_game(game_id):
            self.is_running = True
            self.simulation_task = asyncio.create_task(self._run_loop())
            return True
        return False

    def pause(self):
        """Pauses the simulator stream without resetting the index."""
        if self.is_running:
            self.is_running = False
            print(f"[SIMULATOR] Simulation paused at event index {self.current_idx}/{len(self.events)}.")

    def resume(self) -> bool:
        """Resumes simulation from the current index."""
        if not self.game_id or not self.events:
            print("[SIMULATOR] Cannot resume, no game loaded.")
            return False
            
        if not self.is_running:
            self.is_running = True
            if self.simulation_task and not self.simulation_task.done():
                self.simulation_task.cancel()
            self.simulation_task = asyncio.create_task(self._run_loop())
            print(f"[SIMULATOR] Simulation resumed from event index {self.current_idx}.")
            return True
        return False

    def stop(self):
        """Stops the simulator and resets execution variables."""
        self.is_running = False
        if self.simulation_task and not self.simulation_task.done():
            self.simulation_task.cancel()
        self.current_idx = 0
        self.events = []
        self.game_id = None
        print("[SIMULATOR] Simulation stopped and cleared.")

    def set_speed(self, speed: float):
        """Changes replay playback speed."""
        self.speed_multiplier = max(0.1, min(100.0, speed))
        print(f"[SIMULATOR] Speed multiplier set to {self.speed_multiplier}x.")

    async def _run_loop(self):
        """Asynchronous simulator broadcast engine loop."""
        try:
            print(f"[SIMULATOR] Starting playback loop for game {self.game_id}...")
            while self.is_running and self.current_idx < len(self.events):
                event = self.events[self.current_idx]
                
                # Broadcast the live event dictionary over Websockets
                await self.ws_manager.broadcast_to_game(self.game_id, event)
                
                self.current_idx += 1
                if self.current_idx >= len(self.events):
                    print("[SIMULATOR] End of game sequence reached.")
                    self.is_running = False
                    
                    # Broadcast a termination frame
                    end_msg = {
                        "game_id": self.game_id,
                        "description": "GAME COMPLETED",
                        "is_finished": True,
                        "home_score": event.get("home_score", 0),
                        "away_score": event.get("away_score", 0)
                    }
                    await self.ws_manager.broadcast_to_game(self.game_id, end_msg)
                    break
                    
                # Calculate sleep duration based on game clock differences
                next_event = self.events[self.current_idx]
                time_diff = event["seconds_remaining_in_game"] - next_event["seconds_remaining_in_game"]
                
                # Minimum sleep of 0.1s to prevent flooding on simultaneous events
                if time_diff < 0:
                    time_diff = 0.0
                    
                # Cap the sleep time to prevent freezing on large gaps (e.g. quarter transitions)
                sleep_time = max(0.1, min(10.0, time_diff))
                
                # Apply speed multiplier
                adjusted_sleep = sleep_time / self.speed_multiplier
                await asyncio.sleep(adjusted_sleep)
                
        except asyncio.CancelledError:
            print("[SIMULATOR] Simulation loop background task cancelled.")
        except Exception as e:
            print(f"[SIMULATOR] Unexpected error in simulation loop: {e}")
            self.is_running = False
