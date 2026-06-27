from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps game_id -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        """Accepts a WebSocket connection and registers it for a specific game_id."""
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)
        print(f"[WS_MANAGER] Client connected to game: {game_id}. Active subs: {len(self.active_connections[game_id])}")

    def disconnect(self, websocket: WebSocket, game_id: str):
        """Removes a connection from the registry for a specific game_id."""
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
                print(f"[WS_MANAGER] Client disconnected from game: {game_id}. Active subs: {len(self.active_connections[game_id])}")
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast_to_game(self, game_id: str, message: dict):
        """Sends a JSON message to all clients subscribed to a specific game_id."""
        if game_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WS_MANAGER] Failed to send message to client on game {game_id}: {e}")
                    dead_connections.append(connection)
            
            # Clean up any dead connections encountered during broadcast
            for dead_conn in dead_connections:
                self.disconnect(dead_conn, game_id)

    async def broadcast_global(self, message: dict):
        """Sends a JSON message to all connected clients across all games."""
        for game_id in list(self.active_connections.keys()):
            await self.broadcast_to_game(game_id, message)
