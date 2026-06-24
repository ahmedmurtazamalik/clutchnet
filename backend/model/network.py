import torch
import torch.nn as nn

class WinProbabilityNet(nn.Module):
    def __init__(self, input_dim: int = 13):
        super(WinProbabilityNet, self).__init__()
        # Deeper, wider feed-forward neural network specifically scaled for large dataset
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(128, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.1),
            
            nn.Linear(64, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
            
            nn.Linear(32, 1),
            # Sigmoid outputs probability in range [0, 1]
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
