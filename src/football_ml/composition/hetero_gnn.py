"""Heterogeneous Graph Transformer over relational football data."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from torch_geometric.data import HeteroData
from torch_geometric.nn import HGTConv

from football_ml.base import CompositionModule
from football_ml.config import HeteroGNNConfig


class HeteroGNN(CompositionModule):
    """Heterogeneous Graph Transformer over relational data tables.

    Node types correspond to database tables (matches, match_stats, teams,
    competitions, optionally match_events). Edge types correspond to FK
    relationships plus their reverses.

    Teams and competitions use learned embeddings (no raw numeric features).
    Other node types use linear projections from raw features to d_model.

    Readout: extract team embeddings for home and away teams, concatenate
    to produce a match representation of dimension ``readout_dim``.
    """

    def __init__(
        self,
        config: HeteroGNNConfig,
        metadata: tuple[list[str], list[tuple[str, str, str]]],
        num_teams: int,
        num_competitions: int,
        feature_dims: dict[str, int] | None = None,
    ) -> None:
        super().__init__()
        self.output_dim = config.readout_dim
        self.d_model = config.d_model
        self._node_types = metadata[0]

        # Learned embeddings for entity nodes (no useful numeric features)
        self.team_embedding = nn.Embedding(num_teams, config.d_model)
        self.competition_embedding = nn.Embedding(num_competitions, config.d_model)

        # Per-node-type input projections
        self.input_projections = nn.ModuleDict()
        if feature_dims:
            for node_type, in_dim in feature_dims.items():
                if node_type not in ("teams", "competitions"):
                    self.input_projections[node_type] = nn.Linear(in_dim, config.d_model)
        self._projections_initialized = feature_dims is not None

        # HGT convolution layers
        self.convs = nn.ModuleList()
        for _ in range(config.num_layers):
            self.convs.append(
                HGTConv(
                    in_channels=config.d_model,
                    out_channels=config.d_model,
                    metadata=metadata,
                    heads=config.num_heads,
                )
            )

        self.dropout = nn.Dropout(config.dropout)

    def _ensure_projections(self, data: HeteroData) -> None:
        """Lazily initialize input projections if not set at init."""
        if self._projections_initialized:
            return

        for node_type in self._node_types:
            if node_type in ("teams", "competitions"):
                continue
            if node_type in data.node_types and hasattr(data[node_type], "x"):
                in_dim = data[node_type].x.shape[1]
                self.input_projections[node_type] = nn.Linear(
                    in_dim, self.d_model
                ).to(data[node_type].x.device)

        self._projections_initialized = True

    def _project_features(self, data: HeteroData) -> dict[str, Tensor]:
        """Project all node features to d_model dimension."""
        x_dict: dict[str, Tensor] = {}

        for node_type in data.node_types:
            if node_type == "teams":
                # Use sequential indices [0..N-1] for embedding lookup
                n = data[node_type].num_nodes
                indices = torch.arange(n, device=data[node_type].x.device)
                x_dict[node_type] = self.team_embedding(indices)
            elif node_type == "competitions":
                n = data[node_type].num_nodes
                indices = torch.arange(n, device=data[node_type].x.device)
                x_dict[node_type] = self.competition_embedding(indices)
            elif node_type in self.input_projections:
                x_dict[node_type] = self.input_projections[node_type](
                    data[node_type].x
                )
            else:
                # Fallback: zero features projected
                n = data[node_type].num_nodes
                device = next(self.parameters()).device
                x_dict[node_type] = torch.zeros(
                    n, self.d_model, device=device
                )

        return x_dict

    def forward(
        self,
        data: HeteroData,
        home_team_idx: Tensor,
        away_team_idx: Tensor,
    ) -> Tensor:
        """Forward pass: run HGT on snapshot, extract and concat team embeddings.

        Args:
            data: HeteroData snapshot graph with node features and edge indices.
            home_team_idx: (batch,) indices of home teams in the ``teams``
                node list.
            away_team_idx: (batch,) indices of away teams in the ``teams``
                node list.

        Returns:
            Match representation of shape ``(batch, readout_dim)`` where
            ``readout_dim = 2 * d_model``.
        """
        self._ensure_projections(data)

        # Project all node features to d_model
        x_dict = self._project_features(data)

        # Message passing through HGT layers
        for conv in self.convs:
            x_dict = conv(x_dict, data.edge_index_dict)
            x_dict = {
                k: self.dropout(v.relu()) for k, v in x_dict.items()
            }

        # Team-level readout
        team_embeds = x_dict["teams"]  # (num_teams, d_model)
        home_emb = team_embeds[home_team_idx]  # (batch, d_model)
        away_emb = team_embeds[away_team_idx]  # (batch, d_model)

        return torch.cat([home_emb, away_emb], dim=-1)  # (batch, 2*d_model)
