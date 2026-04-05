"""Player stat prediction head: individual player statistics."""

import torch
from torch import Tensor, nn

from football_ml.base import PredictionHead
from football_ml.config import PlayerStatHeadConfig


class PlayerStatHead(PredictionHead):
    """Predict per-player statistics (goals, assists, shots, etc.)."""

    def __init__(self, config: PlayerStatHeadConfig) -> None:
        super().__init__()
        self.num_stats = config.num_stats

        self.head = nn.Sequential(
            nn.Linear(config.input_dim, config.input_dim // 2),
            nn.ReLU(),
            nn.Linear(config.input_dim // 2, config.num_stats),
        )

    def forward(self, temporal_state: Tensor) -> Tensor:
        """Predict player statistics.

        Args:
            temporal_state: Shape (batch, input_dim).

        Returns:
            Predicted stats of shape (batch, num_stats).
        """
        return self.head(temporal_state)
