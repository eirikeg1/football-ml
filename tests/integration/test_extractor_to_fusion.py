"""Integration test: feature extractors → fusion layer."""

import pytest
import torch

from football_ml.config import PipelineConfig
from football_ml.feature_extractors import (
    MatchContextEncoder,
    PlayerProfileEncoder,
    TeamPerformanceEncoder,
)
from football_ml.fusion import TransformerFusion

BATCH_SIZE = 4


@pytest.mark.integration
class TestExtractorToFusion:
    def test_extractors_feed_into_transformer_fusion(self, config):
        """Feature extractor outputs should be accepted by the fusion layer."""
        profile_enc = PlayerProfileEncoder(config.feature_extractors.player_profile)
        team_enc = TeamPerformanceEncoder(config.feature_extractors.team_performance)
        context_enc = MatchContextEncoder(config.feature_extractors.match_context)
        fusion = TransformerFusion(config.fusion)

        profile_emb = profile_enc(torch.randn(BATCH_SIZE, config.feature_extractors.player_profile.input_dim))
        team_emb = team_enc(torch.randn(BATCH_SIZE, config.feature_extractors.team_performance.input_dim))
        context_emb = context_enc(torch.randn(BATCH_SIZE, config.feature_extractors.match_context.input_dim))

        out = fusion([profile_emb, team_emb, context_emb])
        assert out.shape == (BATCH_SIZE, config.fusion.output_dim)
        assert torch.isfinite(out).all()

    def test_subset_of_extractors(self, config):
        """Fusion should work with any subset of feature extractors."""
        team_enc = TeamPerformanceEncoder(config.feature_extractors.team_performance)
        fusion = TransformerFusion(config.fusion)

        team_emb = team_enc(torch.randn(BATCH_SIZE, config.feature_extractors.team_performance.input_dim))

        out = fusion([team_emb])
        assert out.shape == (BATCH_SIZE, config.fusion.output_dim)
