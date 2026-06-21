import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
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
TARGET_COL = "label"

class GameStateDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.X)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))

def compute_calibration_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10):
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = []
    true_probabilities = []
    pred_probabilities = []
    
    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i+1]
        mask = (y_prob >= lower) & (y_prob < upper) if i < n_bins - 1 else (y_prob >= lower) & (y_prob <= upper)
        
        if np.sum(mask) > 0:
            bin_centers.append((lower + upper) / 2.0)
            true_probabilities.append(np.mean(y_true[mask]))
            pred_probabilities.append(np.mean(y_prob[mask]))
            
    return true_probabilities, pred_probabilities, bin_centers

def train_model():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
    train_path = os.path.join(data_dir, "train_features.csv")
    val_path = os.path.join(data_dir, "val_features.csv")
    test_path = os.path.join(data_dir, "test_features.csv")
    
    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Processed training features not found at {train_path}. Run preprocessor first.")
        
    # Load datasets
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)
    
    print(f"Loaded {len(train_df)} training samples, {len(val_df)} validation samples, and {len(test_df)} test samples.")
    
    # Extract features and targets
    X_train_raw = train_df[FEATURE_COLS].values
    y_train = train_df[TARGET_COL].values
    
    X_val_raw = val_df[FEATURE_COLS].values
    y_val = val_df[TARGET_COL].values
    
    X_test_raw = test_df[FEATURE_COLS].values
    y_test = test_df[TARGET_COL].values
    
    # Scale features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_val = scaler.transform(X_val_raw)
    X_test = scaler.transform(X_test_raw)
    
    # Save scaler parameters for quick, dependency-free scaling at inference time
    scaler_params = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist()
    }
    scaler_path = os.path.join(os.path.dirname(__file__), "scaler.json")
    with open(scaler_path, "w") as f:
        json.dump(scaler_params, f)
    print(f"Saved scaler parameters to {scaler_path}")
    
    # Create datasets and dataloaders
    train_dataset = GameStateDataset(X_train, y_train)
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    
    # Initialize model
    model = WinProbabilityNet(input_dim=len(FEATURE_COLS))
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    
    # Training Loop
    epochs = 40
    best_val_loss = float("inf")
    weights_path = os.path.join(os.path.dirname(__file__), "weights.pt")
    
    print("Training neural network...")
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * X_batch.size(0)
            
        train_loss /= len(train_dataset)
        
        # Validation
        model.eval()
        with torch.no_grad():
            X_val_tensor = torch.tensor(X_val, dtype=torch.float32)
            y_val_tensor = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)
            val_outputs = model(X_val_tensor)
            val_loss = criterion(val_outputs, y_val_tensor).item()
            
        # Early Stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), weights_path)
            
        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:02d}/{epochs:02d} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f}")
            
    print(f"Training completed. Best Val Loss: {best_val_loss:.4f}. Model weights saved to {weights_path}")
    
    # Load best model for evaluation
    model.load_state_dict(torch.load(weights_path))
    model.eval()
    
    with torch.no_grad():
        train_probs = model(torch.tensor(X_train, dtype=torch.float32)).numpy().squeeze()
        val_probs = model(torch.tensor(X_val, dtype=torch.float32)).numpy().squeeze()
        test_probs = model(torch.tensor(X_test, dtype=torch.float32)).numpy().squeeze()
        
    # Evaluate
    print("\n=== Model Evaluation ===")
    
    train_brier = compute_brier_score(y_train, train_probs)
    val_brier = compute_brier_score(y_val, val_probs)
    test_brier = compute_brier_score(y_test, test_probs)
    
    print(f"Brier Score (Train): {train_brier:.4f}")
    print(f"Brier Score (Val):   {val_brier:.4f}")
    print(f"Brier Score (Test):  {test_brier:.4f}")
    
    # Accuracy checks
    train_acc = np.mean((train_probs >= 0.5) == y_train)
    val_acc = np.mean((val_probs >= 0.5) == y_val)
    test_acc = np.mean((test_probs >= 0.5) == y_test)
    
    print(f"Accuracy (Train):    {train_acc * 100:.2f}%")
    print(f"Accuracy (Val):      {val_acc * 100:.2f}%")
    print(f"Accuracy (Test):     {test_acc * 100:.2f}%")
    
    # Calibration details
    print("\nCalibration Check (Test Set Binning):")
    true_p, pred_p, centers = compute_calibration_curve(y_test, test_probs)
    print(f"  {'Bin range':<12} | {'Avg Pred Prob':<15} | {'Empirical Win Rate':<20}")
    print(f"  {'-'*12} | {'-'*15} | {'-'*20}")
    for tp, pp, c in zip(true_p, pred_p, centers):
        print(f"  {c-0.05:0.2f}-{c+0.05:0.2f}     | {pp:15.3f} | {tp:20.3f}")

if __name__ == "__main__":
    train_model()
