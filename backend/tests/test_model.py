import unittest
import os
import time
from backend.model.network import WinProbabilityNet
from backend.model.predictor import Predictor

class TestModelAndPredictor(unittest.TestCase):
    
    def setUp(self):
        # We assume training has run and assets are available
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
        
    def test_network_dimensions(self):
        import torch
        net = WinProbabilityNet(input_dim=19)
        x = torch.randn(5, 19) # Batch of 5
        out = net(x)
        self.assertEqual(out.shape, (5, 1))
        self.assertTrue(torch.all(out >= 0.0) and torch.all(out <= 1.0))
        
    def test_predictor_inference(self):
        # Initialize predictor
        predictor = Predictor(model_dir=self.model_dir)
        
        # Define a mock state
        mock_state = {
            "period": 1.0,
            "seconds_remaining_in_period": 720.0,
            "seconds_remaining_in_game": 2880.0,
            "home_score": 0.0,
            "away_score": 0.0,
            "score_margin": 0.0,
            "possession": 1.0,
            "home_timeouts_remaining": 7.0,
            "away_timeouts_remaining": 7.0,
            "home_fouls": 0.0,
            "away_fouls": 0.0,
            "home_pregame_rating": 1500.0,
            "away_pregame_rating": 1500.0,
            "is_overtime": 0.0,
            "is_clutch": 0.0,
            "largest_lead": 0.0,
            "lead_changes": 0.0,
            "home_pts_last_3_min": 0.0,
            "away_pts_last_3_min": 0.0
        }
        
        prob = predictor.predict(mock_state)
        self.assertIsInstance(prob, float)
        self.assertTrue(0.0 <= prob <= 1.0)
        
        # Test extreme cases (e.g. Home team winning by 40 late in 4th quarter)
        home_dominant_state = mock_state.copy()
        home_dominant_state.update({
            "period": 4.0,
            "seconds_remaining_in_period": 30.0,
            "seconds_remaining_in_game": 30.0,
            "home_score": 120.0,
            "away_score": 80.0,
            "score_margin": 40.0,
            "possession": 1.0,
            "home_timeouts_remaining": 5.0,
            "away_timeouts_remaining": 2.0
        })
        prob_dominant = predictor.predict(home_dominant_state)
        # Probability of home winning should be near-certain (e.g. > 0.95)
        self.assertGreater(prob_dominant, 0.90)
        
        # Test performance (latency must be under 10ms on CPU)
        start_time = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            _ = predictor.predict(mock_state)
        duration = (time.perf_counter() - start_time) / iterations * 1000 # ms
        
        print(f"\nAverage Predictor Inference Latency: {duration:.4f} ms")
        self.assertLess(duration, 10.0, "Predictor is too slow (exceeded 10ms threshold)")

if __name__ == '__main__':
    unittest.main()
