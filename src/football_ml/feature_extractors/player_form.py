"""Player form encoder: recent match stats sequence → form embedding."""

import torch
from torch import Tensor, nn

from football_ml.base import FeatureExtractor
from football_ml.config import PlayerFormConfig


class PlayerFormEncoder(FeatureExtractor):
    """Encode a player's recent match statistics into a form embedding.

    Uses a GRU over a sequence of per-match stat vectors to capture
    current performance trajectory.
    """

    def __init__(self, config: PlayerFormConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        self.gru = nn.GRU(
            input_size=config.input_dim,
            hidden_size=config.hidden_dim,
            batch_first=True,
        )
        self.projection = nn.Linear(config.hidden_dim, config.output_dim)

    def forward(self, x: Tensor) -> Tensor:
        """Encode a sequence of recent match stats.

        Args:
            x: Per-match stat vectors, shape (batch, seq_len, input_dim).

        Returns:
            Form embedding of shape (batch, output_dim).
        """
        _, hidden = self.gru(x)  # hidden: (1, batch, hidden_dim)
        return self.projection(hidden.squeeze(0))
