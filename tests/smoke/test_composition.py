"""Smoke tests: forward pass through lineup GNN."""

import pytest
import torch

from football_ml.composition import LineupGNN

BATCH_SIZE = 4


@pytest.mark.smoke
class TestLineupGNN:
    def test_forward_shape(self, lineup_batch, config):
        cfg = config.composition.lineup_gnn
        gnn = LineupGNN(cfg)
        out = gnn(lineup_batch)
        assert out.shape == (BATCH_SIZE, cfg.output_dim)

    def test_output_is_finite(self, lineup_batch, config):
        gnn = LineupGNN(config.composition.lineup_gnn)
        out = gnn(lineup_batch)
        assert torch.isfinite(out).all()
