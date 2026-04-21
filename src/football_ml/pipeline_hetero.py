"""HeteroGNN pipeline: HeteroData graph → team embeddings → temporal → prediction."""

import torch
from torch import Tensor, nn
from torch_geometric.data import HeteroData

from football_ml.composition.hetero_gnn import HeteroGNN
from football_ml.config import PipelineConfig
from football_ml.heads import MatchOutcomeHead, MatchStatHead, PlayerStatHead, ScorelineHead
from football_ml.temporal import GRUTemporal


class HeteroPipeline(nn.Module):
    """Full prediction pipeline using HeteroGNN.

    Replaces the multi-stage feature extractor + fusion approach with a
    single HeteroGNN that learns entity representations from the relational
    graph structure. The temporal model and prediction heads remain the same.

    Architecture:
        HeteroGNN(snapshot) → match_repr → GRU temporal → prediction head
    """

    def __init__(
        self,
        config: PipelineConfig,
        metadata: tuple[list[str], list[tuple[str, str, str]]],
        num_teams: int,
        num_competitions: int,
        head: str = "match_outcome",
        feature_dims: dict[str, int] | None = None,
    ) -> None:
        super().__init__()

        # Layer 1-3 replacement: HeteroGNN
        self.hetero_gnn = HeteroGNN(
            config.composition.hetero_gnn,
            metadata,
            num_teams,
            num_competitions,
            feature_dims=feature_dims,
        )

        # Layer 4: Temporal
        self.temporal = GRUTemporal(config.temporal)

        # Layer 5: Prediction head
        head_map = {
            "match_outcome": lambda: MatchOutcomeHead(config.heads.match_outcome),
            "scoreline": lambda: ScorelineHead(config.heads.scoreline),
            "player_stat": lambda: PlayerStatHead(config.heads.player_stat),
            "match_stat": lambda: MatchStatHead(config.heads.match_stat),
        }
        if head not in head_map:
            raise ValueError(
                f"Unknown head: {head}. Choose from {list(head_map.keys())}"
            )
        self.head = head_map[head]()

    def forward(
        self,
        data: HeteroData,
        home_team_idx: Tensor,
        away_team_idx: Tensor,
        seq_len: int = 1,
    ) -> Tensor:
        """Full forward pass through the HeteroGNN pipeline.

        Args:
            data: HeteroData snapshot graph.
            home_team_idx: (batch,) home team node indices.
            away_team_idx: (batch,) away team node indices.
            seq_len: number of time steps for temporal model.

        Returns:
            Prediction from the selected head.
        """
        # HeteroGNN → match representation
        match_repr = self.hetero_gnn(data, home_team_idx, away_team_idx)

        # Temporal (create sequence by repeating for demo;
        # real training builds actual sequences from recent matches)
        sequence = match_repr.unsqueeze(1).expand(-1, seq_len, -1)
        temporal_state = self.temporal(sequence)

        # Prediction
        return self.head(temporal_state)
