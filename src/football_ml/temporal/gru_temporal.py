"""GRU temporal model: sequence of match representations → temporal state."""

import torch
from torch import Tensor, nn

from football_ml.base import TemporalModule
from football_ml.config import TemporalConfig


class GRUTemporal(TemporalModule):
    """GRU-based temporal model over match representation sequences.

    Processes a sequence of match-level embeddings (from the fusion layer)
    to produce a temporal state capturing form trajectory and dynamics.
    """

    def __init__(self, config: TemporalConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        self.gru = nn.GRU(
            input_size=config.input_dim,
            hidden_size=config.hidden_dim,
            num_layers=config.num_layers,
            batch_first=True,
        )
        self.projection = nn.Linear(config.hidden_dim, config.output_dim)

    def forward(self, sequence: Tensor) -> Tensor:
        """Process a sequence of match representations.

        Args:
            sequence: Match representation sequence,
                      shape (batch, seq_len, input_dim).

        Returns:
            Temporal state of shape (batch, output_dim).
        """
        _, hidden = self.gru(sequence)
        # Take the last layer's hidden state
        last_hidden = hidden[-1]  # (batch, hidden_dim)
        return self.projection(last_hidden)
