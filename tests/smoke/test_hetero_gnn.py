"""Smoke tests: forward pass through HeteroGNN and HeteroPipeline."""

import pytest
import torch

from football_ml.composition.hetero_gnn import HeteroGNN
from football_ml.pipeline_hetero import HeteroPipeline

NUM_TEAMS = 4
NUM_COMPETITIONS = 1
BATCH_SIZE = 2


@pytest.mark.smoke
class TestHeteroGNN:
    def test_forward_shape(self, sample_hetero_data, hetero_config):
        data, metadata = sample_hetero_data
        cfg = hetero_config.composition.hetero_gnn
        gnn = HeteroGNN(cfg, metadata, NUM_TEAMS, NUM_COMPETITIONS)

        home_idx = torch.tensor([0, 1])
        away_idx = torch.tensor([2, 3])
        out = gnn(data, home_idx, away_idx)

        assert out.shape == (BATCH_SIZE, cfg.readout_dim)

    def test_output_is_finite(self, sample_hetero_data, hetero_config):
        data, metadata = sample_hetero_data
        cfg = hetero_config.composition.hetero_gnn
        gnn = HeteroGNN(cfg, metadata, NUM_TEAMS, NUM_COMPETITIONS)

        home_idx = torch.tensor([0, 1])
        away_idx = torch.tensor([2, 3])
        out = gnn(data, home_idx, away_idx)

        assert torch.isfinite(out).all()

    def test_single_sample(self, sample_hetero_data, hetero_config):
        """Test with a single match (batch_size=1)."""
        data, metadata = sample_hetero_data
        cfg = hetero_config.composition.hetero_gnn
        gnn = HeteroGNN(cfg, metadata, NUM_TEAMS, NUM_COMPETITIONS)

        home_idx = torch.tensor([0])
        away_idx = torch.tensor([1])
        out = gnn(data, home_idx, away_idx)

        assert out.shape == (1, cfg.readout_dim)


@pytest.mark.smoke
class TestHeteroPipeline:
    def test_forward_shape(self, sample_hetero_data, hetero_config):
        data, metadata = sample_hetero_data
        pipeline = HeteroPipeline(
            hetero_config, metadata, NUM_TEAMS, NUM_COMPETITIONS,
            head="match_outcome",
        )

        home_idx = torch.tensor([0, 1])
        away_idx = torch.tensor([2, 3])
        out = pipeline(data, home_idx, away_idx)

        assert out.shape == (BATCH_SIZE, 3)  # 3 classes for match_outcome

    def test_output_is_finite(self, sample_hetero_data, hetero_config):
        data, metadata = sample_hetero_data
        pipeline = HeteroPipeline(
            hetero_config, metadata, NUM_TEAMS, NUM_COMPETITIONS,
            head="match_outcome",
        )

        home_idx = torch.tensor([0, 1])
        away_idx = torch.tensor([2, 3])
        out = pipeline(data, home_idx, away_idx)

        assert torch.isfinite(out).all()

    def test_scoreline_head(self, sample_hetero_data, hetero_config):
        data, metadata = sample_hetero_data
        pipeline = HeteroPipeline(
            hetero_config, metadata, NUM_TEAMS, NUM_COMPETITIONS,
            head="scoreline",
        )

        home_idx = torch.tensor([0, 1])
        away_idx = torch.tensor([2, 3])
        out = pipeline(data, home_idx, away_idx)

        # scoreline outputs (batch, 2, max_goals+1)
        assert out.shape[0] == BATCH_SIZE
        assert torch.isfinite(out).all()
