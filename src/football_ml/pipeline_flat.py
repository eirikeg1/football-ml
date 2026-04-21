"""Simple MLP pipeline for flat feature vectors (no GNN, no fusion)."""

import torch
from torch import Tensor, nn


class FlatPipeline(nn.Module):
    """Direct MLP: flat features -> prediction.

    For use when the input is a pre-computed feature vector (e.g.,
    rolling historical averages) rather than multi-modal data.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 3,
        dropout: float = 0.3,
        num_classes: int = 3,
    ) -> None:
        super().__init__()

        layers: list[nn.Module] = []
        in_dim = input_dim
        for _ in range(num_layers - 1):
            layers.extend([
                nn.Linear(in_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            in_dim = hidden_dim

        layers.append(nn.Linear(in_dim, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, features: Tensor) -> Tensor:
        """Forward pass.

        Args:
            features: (batch, input_dim) flat feature vector.

        Returns:
            (batch, num_classes) logits.
        """
        return self.net(features)
