import os
import sqlite3
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.model.predictor import Predictor
from backend.ws_manager import ConnectionManager
from backend.simulator import ReplaySimulator
from backend.live_poller import LiveGamePoller

# Database Path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "raw", "clutchnet_cache.db")

class SimulatorControl(BaseModel):
    action: str  # "start", "pause", "resume", "stop", "speed"
    game_id: Optional[str] = None
    speed: Optional[float] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles FastAPI application startup and shutdown lifecycles."""
    print("[SERVER] Starting up ClutchNet Backend Server...")
    
    # 1. Initialize core AI and WebSocket manager modules
    predictor = Predictor()
    ws_manager = ConnectionManager()
    
    # 2. Initialize Simulator and Live Poller tasks
    simulator = ReplaySimulator(predictor, ws_manager)
    poller = LiveGamePoller(predictor, ws_manager)
    
    # 3. Cache objects in app state for access in endpoints
    app.state.predictor = predictor
    app.state.ws_manager = ws_manager
    app.state.simulator = simulator
    app.state.poller = poller
    
    # 4. Start the background live NBA poller
    poller.start()
    
    yield
    
    # Clean up tasks on shutdown
    print("[SERVER] Shutting down ClutchNet Backend Server...")
    poller.stop()
    simulator.stop()

app = FastAPI(
    title="ClutchNet API",
    description="Real-Time NBA Win Probability & Game State Serving Engine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits Next.js frontend or CLI testing tools
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST Endpoints
@app.get("/api/games", response_model=List[Dict[str, Any]])
def list_games():
    """Queries and returns a list of all cached regular season and synthetic games."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500, 
            detail=f"SQLite Database file not found at {DB_PATH}. Run scraping pipeline first."
        )
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, season, game_date, matchup, home_team_abbr, away_team_abbr 
            FROM games_list 
            ORDER BY game_date DESC, game_id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        games = [
            {
                "game_id": row[0],
                "season": row[1],
                "game_date": row[2],
                "matchup": row[3],
                "home_team_abbr": row[4],
                "away_team_abbr": row[5]
            }
            for row in rows
        ]
        return games
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/api/games/season/{season}", response_model=List[Dict[str, Any]])
def list_games_by_season(season: str):
    """Queries and returns a list of games for a specific season.
    If no games are cached locally for that season, it dynamically fetches and caches them from the NBA API.
    """
    if not os.path.exists(DB_PATH):
        # Ensure database and tables are initialized
        from backend.data.scraper import get_db_connection
        conn = get_db_connection()
        conn.close()
        
    try:
        # Check if we already have games cached for this season
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM games_list WHERE season = ?", (season,))
        count = cursor.fetchone()[0]
        conn.close()
        
        # If not cached, dynamically scrape the season schedule
        if count == 0:
            print(f"[API] No cached games for season {season}. Fetching schedule dynamically...")
            from backend.data.scraper import fetch_season_games
            # Scrape schedule (lightweight data)
            fetch_season_games(season)
            
        # Retrieve the games list for this season
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, season, game_date, matchup, home_team_abbr, away_team_abbr 
            FROM games_list 
            WHERE season = ?
            ORDER BY game_date DESC, game_id DESC
        """, (season,))
        rows = cursor.fetchall()
        conn.close()
        
        games = [
            {
                "game_id": row[0],
                "season": row[1],
                "game_date": row[2],
                "matchup": row[3],
                "home_team_abbr": row[4],
                "away_team_abbr": row[5]
            }
            for row in rows
        ]
        return games
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load games for season {season}: {e}")

@app.post("/api/simulator/control")
async def control_simulator(control: SimulatorControl):
    """Handles REST controls for starting, pausing, resuming, stopping, and scaling simulation speeds."""
    simulator: ReplaySimulator = app.state.simulator
    action = control.action.lower()
    
    if action == "start":
        if not control.game_id:
            raise HTTPException(status_code=400, detail="Missing game_id for simulator start.")
        if control.speed is not None:
            simulator.set_speed(control.speed)
            
        success = simulator.start(control.game_id)
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Failed to start simulation. Game ID {control.game_id} may not exist in SQLite database."
            )
        return {
            "status": "success", 
            "message": f"Simulation started for game {control.game_id}",
            "speed": simulator.speed_multiplier
        }
        
    elif action == "pause":
        simulator.pause()
        return {"status": "success", "message": "Simulation paused"}
        
    elif action == "resume":
        success = simulator.resume()
        if not success:
            raise HTTPException(status_code=400, detail="No active simulation state loaded to resume.")
        return {"status": "success", "message": "Simulation resumed"}
        
    elif action == "stop":
        simulator.stop()
        return {"status": "success", "message": "Simulation stopped and cleared"}
        
    elif action == "speed":
        if control.speed is None:
            raise HTTPException(status_code=400, detail="Missing speed value for simulator rate scaling.")
        simulator.set_speed(control.speed)
        return {
            "status": "success", 
            "message": f"Simulation speed adjusted to {control.speed}x",
            "speed": simulator.speed_multiplier
        }
        
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid action: '{control.action}'. Supported actions are: start, pause, resume, stop, speed."
        )

@app.get("/api/simulator/status")
async def get_simulator_status():
    """Returns the current state and execution index of the simulator."""
    simulator: ReplaySimulator = app.state.simulator
    return {
        "game_id": simulator.game_id,
        "is_running": simulator.is_running,
        "current_idx": simulator.current_idx,
        "total_events": len(simulator.events),
        "speed_multiplier": simulator.speed_multiplier
    }

# WebSocket route
@app.websocket("/ws/live-game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """Establishes a WebSocket channel, registers the client, and listens for disconnect events."""
    ws_manager: ConnectionManager = app.state.ws_manager
    await ws_manager.connect(websocket, game_id)
    
    try:
        # Keep connection open by listening for client packets (e.g. heartbeat pings)
        while True:
            # Blocks until client sends a message, or raises WebSocketDisconnect on network loss
            data = await websocket.receive_text()
            # If client sends data, echo it or process it as a ping
            await websocket.send_json({"type": "ping_ack", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, game_id)
        print(f"[WS] Client disconnected cleanly from game subscription: {game_id}")
    except Exception as e:
        ws_manager.disconnect(websocket, game_id)
        print(f"[WS] Connection terminated with exception: {e}")
