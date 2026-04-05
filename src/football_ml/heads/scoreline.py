"""Scoreline prediction head: goal distributions per team."""

import torch
from torch import Tensor, nn

from football_ml.base import PredictionHead
from football_ml.config import ScorelineHeadConfig


class ScorelineHead(PredictionHead):
    """Predict goal distributions for home and away teams.

    Outputs logits over discrete goal counts (0 to max_goals) for each team.
    """

    def __init__(self, config: ScorelineHeadConfig) -> None:
        super().__init__()
        self.max_goals = config.max_goals

        self.shared = nn.Sequential(
            nn.Linear(config.input_dim, config.input_dim // 2),
            nn.ReLU(),
        )
        # Separate output for home and away goal distributions
        self.home_goals = nn.Linear(config.input_dim // 2, config.max_goals + 1)
        self.away_goals = nn.Linear(config.input_dim // 2, config.max_goals + 1)

    def forward(self, temporal_state: Tensor) -> Tensor:
        """Predict goal distributions.

        Args:
            temporal_state: Shape (batch, input_dim).

        Returns:
            Logits of shape (batch, 2, max_goals+1) where dim 1 is [home, away].
        """
        shared = self.shared(temporal_state)
        home = self.home_goals(shared)
        away = self.away_goals(shared)
        return torch.stack([home, away], dim=1)
