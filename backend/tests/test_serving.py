import unittest
import os
from fastapi.testclient import TestClient

from backend.main import app

class TestServingAPI(unittest.TestCase):
    
    def test_list_games(self):
        """Verify that list games endpoint returns valid list structures from database."""
        with TestClient(app) as client:
            response = client.get("/api/games")
            self.assertEqual(response.status_code, 200)
            games = response.json()
            self.assertIsInstance(games, list)
            
            # If the database has games, assert key structure
            if len(games) > 0:
                game = games[0]
                self.assertIn("game_id", game)
                self.assertIn("season", game)
                self.assertIn("matchup", game)
                self.assertIn("home_team_abbr", game)
                self.assertIn("away_team_abbr", game)

    def test_simulator_control_flow(self):
        """Tests start, pause, resume, change speed, and stop REST API control states."""
        with TestClient(app) as client:
            # 1. Fetch initial status (should be clear / idle)
            response = client.get("/api/simulator/status")
            self.assertEqual(response.status_code, 200)
            status = response.json()
            self.assertIsNone(status["game_id"])
            self.assertFalse(status["is_running"])
            
            # 2. Trigger simulator start for synthetic game ID "9990000001"
            # Setting high speed multiplier so playback processes quickly in test environment
            response = client.post("/api/simulator/control", json={
                "action": "start",
                "game_id": "9990000001",
                "speed": 50.0
            })
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res["status"], "success")
            
            # Verify updated status
            response = client.get("/api/simulator/status")
            status = response.json()
            self.assertEqual(status["game_id"], "9990000001")
            self.assertTrue(status["is_running"])
            self.assertEqual(status["speed_multiplier"], 50.0)
            
            # 3. Test changing playback speed multiplier
            response = client.post("/api/simulator/control", json={
                "action": "speed",
                "speed": 75.0
            })
            self.assertEqual(response.status_code, 200)
            
            # Verify updated speed
            response = client.get("/api/simulator/status")
            status = response.json()
            self.assertEqual(status["speed_multiplier"], 75.0)
            
            # 4. Trigger pause control
            response = client.post("/api/simulator/control", json={"action": "pause"})
            self.assertEqual(response.status_code, 200)
            
            # Verify status is paused
            response = client.get("/api/simulator/status")
            status = response.json()
            self.assertFalse(status["is_running"])
            self.assertEqual(status["game_id"], "9990000001")
            
            # 5. Trigger resume control
            response = client.post("/api/simulator/control", json={"action": "resume"})
            self.assertEqual(response.status_code, 200)
            
            # Verify status is running again
            response = client.get("/api/simulator/status")
            status = response.json()
            self.assertTrue(status["is_running"])
            
            # 6. Trigger stop control to clear simulator
            response = client.post("/api/simulator/control", json={"action": "stop"})
            self.assertEqual(response.status_code, 200)
            
            # Verify cleared variables
            response = client.get("/api/simulator/status")
            status = response.json()
            self.assertIsNone(status["game_id"])
            self.assertFalse(status["is_running"])

    def test_websocket_broadcast_delivery(self):
        """Verifies that simulator plays get correctly broadcasted to WebSocket subscribers."""
        with TestClient(app) as client:
            # Establish subscription channel
            with client.websocket_connect("/ws/live-game/9990000001") as websocket:
                # Trigger the simulator to start streaming events
                response = client.post("/api/simulator/control", json={
                    "action": "start",
                    "game_id": "9990000001",
                    "speed": 100.0
                })
                self.assertEqual(response.status_code, 200)
                
                # Await and receive broadcast frame from WebSocket
                event_frame = websocket.receive_json()
                
                # Check frame properties
                self.assertEqual(event_frame["game_id"], "9990000001")
                self.assertIn("period", event_frame)
                self.assertIn("seconds_remaining_in_period", event_frame)
                self.assertIn("home_score", event_frame)
                self.assertIn("away_score", event_frame)
                self.assertIn("score_margin", event_frame)
                self.assertIn("possession", event_frame)
                self.assertIn("win_probability", event_frame)
                self.assertIn("play_delta", event_frame)
                self.assertIn("description", event_frame)
                
                # Stop simulator play loop
                client.post("/api/simulator/control", json={"action": "stop"})

if __name__ == "__main__":
    unittest.main()
