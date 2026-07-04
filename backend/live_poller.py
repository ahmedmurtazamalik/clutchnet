import asyncio
import httpx
from typing import Dict, Any, Optional, List
import pandas as pd
import os
import json
from backend.model.predictor import Predictor
from backend.ws_manager import ConnectionManager
from backend.data.scraper import map_v3_to_v2
from backend.data.preprocessor import preprocess_game

# NBA CDN Endpoint URLs
SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard.json"
PBP_URL_TEMPLATE = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nba.com/"
}

class LiveGamePoller:
    def __init__(self, predictor: Predictor, ws_manager: ConnectionManager):
        self.predictor = predictor
        self.ws_manager = ws_manager
        self.is_running = False
        self.poll_task: Optional[asyncio.Task] = None
        self.poll_interval = 5.0 # Poll every 5 seconds
        
        # Track last event ID processed per game to avoid redundant predictions & broadcasts
        # game_id -> last_eventnum
        self.last_event_tracker: Dict[str, int] = {}
        # game_id -> last_win_probability
        self.last_prob_tracker: Dict[str, float] = {}
        
        # Pregame Elos mapping
        self.elos = {}
        elos_path = os.path.join(os.path.dirname(__file__), "model", "latest_elos.json")
        if os.path.exists(elos_path):
            try:
                with open(elos_path, "r") as f:
                    self.elos = json.load(f)
            except Exception as e:
                print(f"[LIVE_POLLER] Failed to load Elos: {e}")

    def start(self):
        """Starts the live polling background task loop."""
        if not self.is_running:
            self.is_running = True
            self.poll_task = asyncio.create_task(self._poll_loop())
            print("[LIVE_POLLER] Background polling task started.")

    def stop(self):
        """Stops the live polling background task loop."""
        self.is_running = False
        if self.poll_task and not self.poll_task.done():
            self.poll_task.cancel()
        print("[LIVE_POLLER] Background polling task stopped.")

    async def _poll_loop(self):
        """Infinite loop querying the active NBA scoreboard and PBP feeds."""
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            while self.is_running:
                try:
                    # Skip querying if no clients are connected to save bandwidth and avoid CDN blocks
                    if not self.ws_manager.active_connections:
                        await asyncio.sleep(self.poll_interval)
                        continue

                    # 1. Fetch the scoreboard to find in-progress games
                    response = await client.get(SCOREBOARD_URL)
                    if response.status_code != 200:
                        print(f"[LIVE_POLLER] Failed to fetch scoreboard. Code: {response.status_code}")
                        await asyncio.sleep(self.poll_interval)
                        continue
                        
                    data = response.json()
                    games = data.get("scoreboard", {}).get("games", [])
                    
                    active_games = []
                    for game in games:
                        # gameStatus == 2 means in-progress (live)
                        # We also only poll if there are active websocket subscriptions to save bandwidth
                        game_id = game.get("gameId")
                        if game.get("gameStatus") == 2 and game_id in self.ws_manager.active_connections:
                            active_games.append(game)
                            
                    if not active_games:
                        # Log status periodically but less frequently if idle
                        print("[LIVE_POLLER] No active subscribed live games found. Sleeping...")
                        await asyncio.sleep(self.poll_interval * 2)
                        continue
                        
                    # 2. Poll play-by-play updates for each active, subscribed live game
                    for game in active_games:
                        game_id = game["gameId"]
                        home_team = game["homeTeam"]
                        away_team = game["awayTeam"]
                        
                        await self._process_live_game(
                            client=client,
                            game_id=game_id,
                            home_id=home_team["teamId"],
                            away_id=away_team["teamId"],
                            home_abbr=home_team["teamTricode"],
                            away_abbr=away_team["teamTricode"]
                        )
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[LIVE_POLLER] Error in poll loop: {e}")
                    
                await asyncio.sleep(self.poll_interval)

    async def _process_live_game(
        self, client: httpx.AsyncClient, game_id: str, 
        home_id: int, away_id: int, home_abbr: str, away_abbr: str
    ):
        """Fetches play-by-play details for a single game, runs inference, and broadcasts events."""
        url = PBP_URL_TEMPLATE.format(game_id=game_id)
        response = await client.get(url)
        if response.status_code != 200:
            print(f"[LIVE_POLLER] Failed to fetch PBP for game {game_id}: {response.status_code}")
            return
            
        data = response.json()
        actions = data.get("game", {}).get("actions", [])
        if not actions:
            return
            
        # Parse the latest action number
        latest_action = actions[-1]
        latest_action_num = int(latest_action.get("actionNumber", 0))
        
        # Check if we have already processed this event
        last_processed = self.last_event_tracker.get(game_id, 0)
        if latest_action_num <= last_processed:
            return
            
        # Convert raw CDN actions to pandas DataFrame
        df_v3 = pd.DataFrame(actions)
        
        # Map CDN V3 schema to standard V2 schema
        df_v2 = map_v3_to_v2(df_v3, home_id, away_id)
        if df_v2.empty:
            return
            
        # Run preprocessing to engineer features
        home_elo = self.elos.get(home_abbr, 1500.0)
        away_elo = self.elos.get(away_abbr, 1500.0)
        
        processed_df = preprocess_game(
            game_id=game_id,
            pbp_df=df_v2,
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_abbr=home_abbr,
            away_team_abbr=away_abbr,
            home_elo=home_elo,
            away_elo=away_elo
        )
        
        if processed_df.empty:
            return
            
        # We broadcast any newly arrived events since the last check
        # We filter the preprocessed DataFrame to only contain eventnums > last_processed
        new_events_df = processed_df[processed_df["eventnum"] > last_processed]
        new_events = new_events_df.to_dict("records")
        
        for event in new_events:
            event["home_team_abbr"] = home_abbr
            event["away_team_abbr"] = away_abbr
            
            # Predict win probability
            try:
                prob = self.predictor.predict(event)
                event["win_probability"] = prob
                
                # Compute delta
                prev_prob = self.last_prob_tracker.get(game_id, 0.5)
                delta = prob - prev_prob
                event["play_delta"] = delta
                
                # Cache the probability
                self.last_prob_tracker[game_id] = prob
            except Exception as e:
                print(f"[LIVE_POLLER] Inference error: {e}")
                event["win_probability"] = 0.5
                event["play_delta"] = 0.0
                
            # Broadcast the live event downstream to subscribers
            await self.ws_manager.broadcast_to_game(game_id, event)
            
        # Update trackers
        self.last_event_tracker[game_id] = latest_action_num
        print(f"[LIVE_POLLER] Broadcasted {len(new_events)} new play updates for game {game_id}.")
