import os
import json
import torch
from typing import Dict, Any, List
from backend.model.network import WinProbabilityNet

import glob

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
        Loads the trained WinProbabilityNet ensemble and feature scaler parameters.
        """
        if model_dir is None:
            model_dir = os.path.dirname(__file__)
            
        # Look for multi-seed ensemble weights
        weights_paths = glob.glob(os.path.join(model_dir, "weights_seed_*.pt"))
        
        # Fallback to single weights.pt for backward compatibility
        if not weights_paths:
            single_path = os.path.join(model_dir, "weights.pt")
            if os.path.exists(single_path):
                weights_paths = [single_path]
                
        scaler_path = os.path.join(model_dir, "scaler.json")
        
        if not weights_paths or not os.path.exists(scaler_path):
            raise FileNotFoundError(
                f"Model assets not found in {model_dir}. Please run model training first."
            )
            
        # Load pre-saved scaler mean and scale standard deviation
        with open(scaler_path, "r") as f:
            scaler_params = json.load(f)
            
        self.mean = torch.tensor(scaler_params["mean"], dtype=torch.float32)
        self.scale = torch.tensor(scaler_params["scale"], dtype=torch.float32)
        
        # Initialize and load all models in the ensemble
        self.models = []
        for w_path in weights_paths:
            model = WinProbabilityNet(input_dim=len(FEATURE_COLS))
            model.load_state_dict(torch.load(w_path, map_location=torch.device("cpu")))
            model.eval()
            self.models.append(model)
            
        print(f"Loaded ensemble with {len(self.models)} model(s) from {model_dir}")
        
    def predict(self, state: Dict[str, Any]) -> float:
        """
        Calculates the average live win probability for the Home team across the ensemble.
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
        
        # Inference across all models (unsqueeze(0) adds the batch dimension: [N] -> [1, N])
        with torch.no_grad():
            x_input = x_scaled.unsqueeze(0)
            probs = [model(x_input).item() for model in self.models]
            prob = sum(probs) / len(probs)
            
        return prob
