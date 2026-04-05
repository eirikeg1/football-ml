"""Team performance encoder: aggregate team stats → embedding."""

import torch
from torch import Tensor, nn

from football_ml.base import FeatureExtractor
from football_ml.config import TeamPerformanceConfig


class TeamPerformanceEncoder(FeatureExtractor):
    """Encode team-level performance statistics (xG, Elo, possession, etc.)."""

    def __init__(self, config: TeamPerformanceConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        self.encoder = nn.Sequential(
            nn.Linear(config.input_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.output_dim),
        )

    def forward(self, x: Tensor) -> Tensor:
        """Encode team performance stats.

        Args:
            x: Team stat vector, shape (batch, input_dim).

        Returns:
            Embedding of shape (batch, output_dim).
        """
        return self.encoder(x)
