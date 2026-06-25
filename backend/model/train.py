import sys
import os

# Add project root to sys.path to resolve 'backend' imports when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from backend.model.network import WinProbabilityNet

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

class SimpleProgressBar:
    def __init__(self, total, prefix="", suffix="", length=30):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.start_time = time.time()
        
    def update(self, current, loss_val=None):
        elapsed = time.time() - self.start_time
        speed = current / elapsed if elapsed > 0 else 0
        eta = (self.total - current) / speed if speed > 0 else 0
        
        percent = 100 * (current / float(self.total))
        filled_length = int(self.length * current // self.total)
        bar = "█" * filled_length + "-" * (self.length - filled_length)
        
        loss_str = f" - Loss: {loss_val:.4f}" if loss_val is not None else ""
        eta_str = f" - ETA: {eta:.1f}s" if current < self.total else f" - Time: {elapsed:.1f}s"
        
        sys.stdout.write(f"\r{self.prefix} |{bar}| {percent:.1f}%{loss_str}{eta_str} {self.suffix}")
        sys.stdout.flush()
        if current == self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

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
    "away_pregame_rating",
    "is_overtime",
    "is_clutch",
    "largest_lead",
    "lead_changes",
    "home_pts_last_3_min",
    "away_pts_last_3_min"
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

def evaluate_loader(model, data_loader, criterion, device):
    """
    Evaluates model loss and predictions over a DataLoader in memory-safe batches.
    """
    model.eval()
    total_loss = 0.0
    all_probs = []
    with torch.no_grad():
        for X_batch, y_batch in data_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item() * X_batch.size(0)
            all_probs.append(outputs.cpu().numpy())
    avg_loss = total_loss / len(data_loader.dataset)
    probs = np.vstack(all_probs).squeeze()
    return avg_loss, probs
def evaluate_ensemble_loader(models, data_loader, device):
    """
    Evaluates raw win probability predictions by averaging outputs across the ensemble.
    """
    for m in models:
        m.eval()
        
    all_probs = []
    with torch.no_grad():
        for X_batch, _ in data_loader:
            X_batch = X_batch.to(device)
            # Collect probabilities from all models in the ensemble
            batch_probs = []
            for m in models:
                outputs = m(X_batch)
                batch_probs.append(outputs.cpu().numpy())
            # Average predictions across ensemble instances (axis 0 is the model index)
            avg_batch_prob = np.mean(np.array(batch_probs), axis=0)
            all_probs.append(avg_batch_prob)
            
    probs = np.vstack(all_probs).squeeze()
    return probs

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
    val_dataset = GameStateDataset(X_val, y_val)
    test_dataset = GameStateDataset(X_test, y_test)
    
    # Validation/Test loaders in memory-safe batch sizes to prevent OOM
    val_loader = DataLoader(val_dataset, batch_size=4096, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=4096, shuffle=False)
    
    # Device detection (GTX 1060 3GB support)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device for training: {device}")
    
    # Ensemble Seeds config
    SEEDS = [42, 123, 456, 789, 999]
    val_losses_by_seed = {}
    
    for seed in SEEDS:
        print(f"\n================ Training Model (Seed: {seed}) ================")
        
        # Seed all random number generators for reproducibility
        import random
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            
        # Create DataLoader with current seed shuffle generator
        g = torch.Generator()
        g.manual_seed(seed)
        train_loader = DataLoader(train_dataset, batch_size=2048, shuffle=True, generator=g)
        
        # Initialize model
        model = WinProbabilityNet(input_dim=len(FEATURE_COLS)).to(device)
        criterion = nn.BCELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
        
        # Learning rate scheduler
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
        # Training Loop config
        epochs = 40
        best_val_loss = float("inf")
        seed_weights_path = os.path.join(os.path.dirname(__file__), f"weights_seed_{seed}.pt")
        
        # Early stopping config
        patience = 5
        epochs_no_improve = 0
        
        print(f"Training network instance (seed {seed})...")
        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            total_batches = len(train_loader)
            
            if HAS_TQDM:
                epoch_iter = tqdm(train_loader, desc=f"Epoch {epoch:02d}/{epochs:02d}", leave=False)
            else:
                pbar = SimpleProgressBar(total_batches, prefix=f"Epoch {epoch:02d}/{epochs:02d}")
                epoch_iter = train_loader
                
            for i, (X_batch, y_batch) in enumerate(epoch_iter):
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)
                
                optimizer.zero_grad()
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * X_batch.size(0)
                
                if HAS_TQDM:
                    epoch_iter.set_postfix({"loss": f"{loss.item():.4f}"})
                else:
                    pbar.update(i + 1, loss.item())
                    
            train_loss /= len(train_dataset)
            
            # Validation in memory-safe batches
            val_loss, val_probs = evaluate_loader(model, val_loader, criterion, device)
            
            # Update scheduler
            scheduler.step(val_loss)
            
            # Checkpoint and Early Stopping Check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), seed_weights_path)
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                
            if epoch % 5 == 0 or epoch == 1:
                val_acc = np.mean((val_probs >= 0.5) == y_val)
                val_auc = roc_auc_score(y_val, val_probs)
                current_lr = optimizer.param_groups[0]['lr']
                print(f"Epoch {epoch:02d}/{epochs:02d} - LR: {current_lr:.6f} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f} - Val Acc: {val_acc*100:.2f}% - Val AUC: {val_auc:.4f}")
                
            if epochs_no_improve >= patience:
                print(f"Early stopping triggered at epoch {epoch}. Best Val Loss: {best_val_loss:.4f}")
                break
                
        val_losses_by_seed[seed] = best_val_loss
        print(f"Seed {seed} completed. Best Val Loss: {best_val_loss:.4f}")
        
    # Copy weights of best performing seed model to weights.pt for fallback single-model serving
    best_overall_seed = min(val_losses_by_seed, key=val_losses_by_seed.get)
    best_overall_val_loss = val_losses_by_seed[best_overall_seed]
    import shutil
    src_path = os.path.join(os.path.dirname(__file__), f"weights_seed_{best_overall_seed}.pt")
    dest_path = os.path.join(os.path.dirname(__file__), "weights.pt")
    shutil.copy(src_path, dest_path)
    print(f"\nCopied best performing seed model {best_overall_seed} (Val Loss: {best_overall_val_loss:.4f}) to {dest_path}")
    
    # Load all models in the ensemble for unified evaluation
    ensemble_models = []
    for seed in SEEDS:
        model_path = os.path.join(os.path.dirname(__file__), f"weights_seed_{seed}.pt")
        m = WinProbabilityNet(input_dim=len(FEATURE_COLS)).to(device)
        m.load_state_dict(torch.load(model_path, map_location=device))
        m.eval()
        ensemble_models.append(m)
        
    # Memory-safe evaluation on all splits using the complete ensemble
    train_probs = evaluate_ensemble_loader(ensemble_models, DataLoader(train_dataset, batch_size=4096, shuffle=False), device)
    val_probs = evaluate_ensemble_loader(ensemble_models, val_loader, device)
    test_probs = evaluate_ensemble_loader(ensemble_models, test_loader, device)
    
    # Evaluate Unified Ensemble
    print("\n=== Unified Ensemble Model Evaluation ===")
    
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
    
    # ROC-AUC checks
    train_auc = roc_auc_score(y_train, train_probs)
    val_auc = roc_auc_score(y_val, val_probs)
    test_auc = roc_auc_score(y_test, test_probs)
    
    print(f"ROC-AUC (Train):     {train_auc:.4f}")
    print(f"ROC-AUC (Val):       {val_auc:.4f}")
    print(f"ROC-AUC (Test):      {test_auc:.4f}")
    
    # Calibration details
    print("\nCalibration Check (Test Set Binning):")
    true_p, pred_p, centers = compute_calibration_curve(y_test, test_probs)
    print(f"  {'Bin range':<12} | {'Avg Pred Prob':<15} | {'Empirical Win Rate':<20}")
    print(f"  {'-'*12} | {'-'*15} | {'-'*20}")
    for tp, pp, c in zip(true_p, pred_p, centers):
        print(f"  {c-0.05:0.2f}-{c+0.05:0.2f}     | {pp:15.3f} | {tp:20.3f}")

if __name__ == "__main__":
    train_model()
