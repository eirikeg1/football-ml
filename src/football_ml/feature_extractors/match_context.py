"""Match context encoder: contextual match features → embedding."""

import torch
from torch import Tensor, nn

from football_ml.base import FeatureExtractor
from football_ml.config import MatchContextConfig


class MatchContextEncoder(FeatureExtractor):
    """Encode match context features (home/away, rest days, competition, etc.)."""

    def __init__(self, config: MatchContextConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        self.encoder = nn.Sequential(
            nn.Linear(config.input_dim, config.output_dim),
            nn.ReLU(),
        )

    def forward(self, x: Tensor) -> Tensor:
        """Encode match context features.

        Args:
            x: Context feature vector, shape (batch, input_dim).

        Returns:
            Embedding of shape (batch, output_dim).
        """
        return self.encoder(x)
