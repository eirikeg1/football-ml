"""Lineup GNN: player embeddings + formation graph → team representation."""

import torch
from torch import Tensor, nn
from torch_geometric.data import Batch, Data
from torch_geometric.nn import GCNConv, global_mean_pool

from football_ml.base import CompositionModule
from football_ml.config import LineupGNNConfig


class LineupGNN(CompositionModule):
    """Graph neural network over a match lineup.

    Nodes are players (with their combined profile + form embeddings).
    Edges represent positional/tactical relationships.
    Produces a team-level embedding via graph pooling.
    """

    def __init__(self, config: LineupGNNConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim

        self.convs = nn.ModuleList()
        in_dim = config.player_dim
        for _ in range(config.num_layers):
            self.convs.append(GCNConv(in_dim, config.hidden_dim))
            in_dim = config.hidden_dim

        self.projection = nn.Linear(config.hidden_dim, config.output_dim)

    def forward(self, data: Batch) -> Tensor:
        """Process a batched graph of player lineups.

        Args:
            data: PyG Batch with:
                - x: node features (num_nodes, player_dim)
                - edge_index: graph connectivity (2, num_edges)
                - batch: batch assignment vector

        Returns:
            Team embedding of shape (batch_size, output_dim).
        """
        x, edge_index, batch = data.x, data.edge_index, data.batch

        for conv in self.convs:
            x = conv(x, edge_index).relu()

        x = global_mean_pool(x, batch)
        return self.projection(x)
