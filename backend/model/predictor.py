import os
import json
import torch
from typing import Dict, Any, List
from backend.model.network import WinProbabilityNet

FEATURE_COLS = [
    "period",
    "seconds_remaining_in_period",
    "seconds_remaining_in_game",
    "home_score",
    "away_score",
    "score_margin",
    "possession",
    "home_timeouts_remaining",
    "away_timeouts_remaining",
    "home_fouls",
    "away_fouls",
    "home_pregame_rating",
    "away_pregame_rating"
]

class Predictor:
    def __init__(self, model_dir: str = None):
        """
        Loads the trained WinProbabilityNet and feature scaler parameters.
        """
        if model_dir is None:
            model_dir = os.path.dirname(__file__)
            
        weights_path = os.path.join(model_dir, "weights.pt")
        scaler_path = os.path.join(model_dir, "scaler.json")
        
        if not os.path.exists(weights_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(
                f"Model assets not found in {model_dir}. Please run model training first."
            )
            
        # Load pre-saved scaler mean and scale standard deviation
        with open(scaler_path, "r") as f:
            scaler_params = json.load(f)
            
        self.mean = torch.tensor(scaler_params["mean"], dtype=torch.float32)
        self.scale = torch.tensor(scaler_params["scale"], dtype=torch.float32)
        
        # Initialize network and load weights
        self.model = WinProbabilityNet(input_dim=len(FEATURE_COLS))
        self.model.load_state_dict(torch.load(weights_path, map_location=torch.device("cpu")))
        self.model.eval()
        
    def predict(self, state: Dict[str, Any]) -> float:
        """
        Calculates the live win probability for the Home team.
        Expects a dictionary with keys matching FEATURE_COLS.
        """
        try:
            # Build feature array in strict expected order
            feats = [float(state[col]) for col in FEATURE_COLS]
        except KeyError as e:
            raise KeyError(f"Missing required game state feature for model inference: {e}")
            
        x = torch.tensor(feats, dtype=torch.float32)
        
        # Perform scaling directly without scikit-learn dependency
        x_scaled = (x - self.mean) / self.scale
        
        # Inference (unsqueeze(0) adds the batch dimension: [N] -> [1, N])
        with torch.no_grad():
            prob = self.model(x_scaled.unsqueeze(0)).item()
            
        return prob
