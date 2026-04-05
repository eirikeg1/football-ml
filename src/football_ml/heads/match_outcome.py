"""Match outcome prediction head: W/D/L probabilities."""

import torch
from torch import Tensor, nn

from football_ml.base import PredictionHead
from football_ml.config import MatchOutcomeHeadConfig


class MatchOutcomeHead(PredictionHead):
    """Predict match outcome as win/draw/loss probabilities."""

    def __init__(self, config: MatchOutcomeHeadConfig) -> None:
        super().__init__()
        self.head = nn.Sequential(
            nn.Linear(config.input_dim, config.input_dim // 2),
            nn.ReLU(),
            nn.Linear(config.input_dim // 2, config.num_classes),
        )

    def forward(self, temporal_state: Tensor) -> Tensor:
        """Predict match outcome probabilities.

        Args:
            temporal_state: Shape (batch, input_dim).

        Returns:
            Logits of shape (batch, num_classes). Apply softmax for probabilities.
        """
        return self.head(temporal_state)
