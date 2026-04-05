"""Integration test: fusion → temporal → prediction head."""

import pytest
import torch

from football_ml.config import PipelineConfig
from football_ml.fusion import TransformerFusion
from football_ml.heads import MatchOutcomeHead, ScorelineHead
from football_ml.temporal import GRUTemporal

BATCH_SIZE = 4
SEQ_LEN = 5


@pytest.mark.integration
class TestFusionToPrediction:
    def _make_match_sequence(self, config) -> torch.Tensor:
        """Simulate a sequence of fused match representations."""
        fusion = TransformerFusion(config.fusion)
        match_reprs = []
        for _ in range(SEQ_LEN):
            embeddings = [
                torch.randn(BATCH_SIZE, 64),
                torch.randn(BATCH_SIZE, 32),
            ]
            match_reprs.append(fusion(embeddings))
        return torch.stack(match_reprs, dim=1)  # (batch, seq_len, fusion_output_dim)

    def test_fusion_to_temporal_to_outcome(self, config):
        """Full downstream path: fusion → GRU → match outcome head."""
        sequence = self._make_match_sequence(config)
        temporal = GRUTemporal(config.temporal)
        head = MatchOutcomeHead(config.heads.match_outcome)

        temporal_state = temporal(sequence)
        prediction = head(temporal_state)

        assert prediction.shape == (BATCH_SIZE, config.heads.match_outcome.num_classes)
        assert torch.isfinite(prediction).all()

    def test_fusion_to_temporal_to_scoreline(self, config):
        """Full downstream path: fusion → GRU → scoreline head."""
        sequence = self._make_match_sequence(config)
        temporal = GRUTemporal(config.temporal)
        head = ScorelineHead(config.heads.scoreline)

        temporal_state = temporal(sequence)
        prediction = head(temporal_state)

        assert prediction.shape == (BATCH_SIZE, 2, config.heads.scoreline.max_goals + 1)
        assert torch.isfinite(prediction).all()
