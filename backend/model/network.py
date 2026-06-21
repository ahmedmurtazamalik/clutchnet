import torch
import torch.nn as nn

class WinProbabilityNet(nn.Module):
    def __init__(self, input_dim: int = 13):
        super(WinProbabilityNet, self).__init__()
        # Feed-forward neural network
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            # Sigmoid outputs probability in range [0, 1]
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
