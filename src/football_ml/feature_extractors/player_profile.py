"""Player profile encoder: FM attributes → learned embedding."""

import torch
from torch import Tensor, nn

from football_ml.base import FeatureExtractor
from football_ml.config import PlayerProfileConfig


class PlayerProfileEncoder(FeatureExtractor):
    """Encode Football Manager player attributes into a dense embedding.

    Uses an MLP with configurable depth. Can be pretrained via multi-task
    learning (predict position + market value) and then used as a frozen
    or fine-tuned feature extractor.
    """

    def __init__(self, config: PlayerProfileConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        layers: list[nn.Module] = []
        in_dim = config.input_dim
        for _ in range(config.num_layers - 1):
            layers.extend([
                nn.Linear(in_dim, config.hidden_dim),
                nn.ReLU(),
            ])
            in_dim = config.hidden_dim
        layers.append(nn.Linear(in_dim, config.output_dim))

        self.encoder = nn.Sequential(*layers)

    def forward(self, x: Tensor) -> Tensor:
        """Encode player attributes.

        Args:
            x: Player attribute vector, shape (batch, input_dim).

        Returns:
            Embedding of shape (batch, output_dim).
        """
        return self.encoder(x)
