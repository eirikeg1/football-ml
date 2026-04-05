"""Match stat prediction head: team-level match statistics."""

import torch
from torch import Tensor, nn

from football_ml.base import PredictionHead
from football_ml.config import MatchStatHeadConfig


class MatchStatHead(PredictionHead):
    """Predict team-level match statistics (possession, shots, xG, corners, etc.)."""

    def __init__(self, config: MatchStatHeadConfig) -> None:
        super().__init__()
        self.num_stats = config.num_stats

        self.head = nn.Sequential(
            nn.Linear(config.input_dim, config.input_dim // 2),
            nn.ReLU(),
            nn.Linear(config.input_dim // 2, config.num_stats),
        )

    def forward(self, temporal_state: Tensor) -> Tensor:
        """Predict team-level match statistics.

        Args:
            temporal_state: Shape (batch, input_dim).

        Returns:
            Predicted stats of shape (batch, num_stats).
        """
        return self.head(temporal_state)
