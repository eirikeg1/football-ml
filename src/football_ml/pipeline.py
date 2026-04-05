"""Full pipeline wiring: config → instantiated modules → forward pass."""

import torch
from torch import Tensor, nn
from torch_geometric.data import Batch

from football_ml.composition import LineupGNN
from football_ml.config import PipelineConfig
from football_ml.feature_extractors import (
    MatchContextEncoder,
    PlayerFormEncoder,
    PlayerProfileEncoder,
    TeamPerformanceEncoder,
)
from football_ml.fusion import HybridFusion, TransformerFusion
from football_ml.heads import MatchOutcomeHead, MatchStatHead, PlayerStatHead, ScorelineHead
from football_ml.temporal import GRUTemporal


class FootballPipeline(nn.Module):
    """Full prediction pipeline wired from a PipelineConfig.

    Connects feature extractors → composition (GNN) → fusion → temporal → head.
    """

    def __init__(self, config: PipelineConfig, head: str = "match_outcome") -> None:
        super().__init__()

        # Layer 1: Feature extractors
        self.player_profile_encoder = PlayerProfileEncoder(config.feature_extractors.player_profile)
        self.player_form_encoder = PlayerFormEncoder(config.feature_extractors.player_form)
        self.team_performance_encoder = TeamPerformanceEncoder(config.feature_extractors.team_performance)
        self.match_context_encoder = MatchContextEncoder(config.feature_extractors.match_context)

        # Layer 2: Composition
        self.lineup_gnn = LineupGNN(config.composition.lineup_gnn)

        # Layer 3: Fusion
        if config.fusion.type == "transformer":
            self.fusion = TransformerFusion(config.fusion)
        elif config.fusion.type == "hybrid":
            group_dims = [
                self.team_performance_encoder.output_dim,
                self.match_context_encoder.output_dim,
                self.lineup_gnn.output_dim,
                self.lineup_gnn.output_dim,
            ]
            self.fusion = HybridFusion(config.fusion, group_dims)
        else:
            raise ValueError(f"Unknown fusion type: {config.fusion.type}")

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
            raise ValueError(f"Unknown head: {head}. Choose from {list(head_map.keys())}")
        self.head = head_map[head]()

    def forward(
        self,
        player_profiles: Tensor,
        player_form: Tensor,
        team_performance: Tensor,
        match_context: Tensor,
        home_lineup: Batch,
        away_lineup: Batch,
        seq_len: int = 1,
    ) -> Tensor:
        """Full forward pass through the pipeline.

        For simplicity, this processes a single time step. In training,
        you would call the feature extraction + fusion for each match in
        the sequence, then pass the sequence to the temporal model.

        Args:
            player_profiles: (batch, input_dim) player FM attributes
            player_form: (batch, form_seq_len, input_dim) recent match stats
            team_performance: (batch, input_dim) team-level stats
            match_context: (batch, input_dim) contextual features
            home_lineup: PyG Batch of home team lineup graphs
            away_lineup: PyG Batch of away team lineup graphs
            seq_len: Number of time steps (match representations are repeated
                     for demonstration; real usage builds actual sequences)

        Returns:
            Prediction from the selected head.
        """
        # Layer 1: Extract features
        profile_emb = self.player_profile_encoder(player_profiles)
        form_emb = self.player_form_encoder(player_form)
        team_emb = self.team_performance_encoder(team_performance)
        context_emb = self.match_context_encoder(match_context)

        # Layer 2: Composition (GNN over lineups)
        home_emb = self.lineup_gnn(home_lineup)
        away_emb = self.lineup_gnn(away_lineup)

        # Layer 3: Fusion
        embeddings = [team_emb, context_emb, home_emb, away_emb]
        match_repr = self.fusion(embeddings)

        # Layer 4: Temporal (create a sequence by repeating for demo)
        # In real usage, match_repr would be computed per time step
        sequence = match_repr.unsqueeze(1).expand(-1, seq_len, -1)
        temporal_state = self.temporal(sequence)

        # Layer 5: Prediction
        return self.head(temporal_state)
