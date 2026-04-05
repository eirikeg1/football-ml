"""Smoke tests: forward pass through temporal model."""

import pytest
import torch

from football_ml.temporal import GRUTemporal

BATCH_SIZE = 4
SEQ_LEN = 10


@pytest.mark.smoke
class TestGRUTemporal:
    def test_forward_shape(self, config):
        temporal = GRUTemporal(config.temporal)
        x = torch.randn(BATCH_SIZE, SEQ_LEN, config.temporal.input_dim)
        out = temporal(x)
        assert out.shape == (BATCH_SIZE, config.temporal.output_dim)

    def test_different_seq_lengths(self, config):
        """Should handle any sequence length."""
        temporal = GRUTemporal(config.temporal)
        for seq_len in [1, 5, 20]:
            x = torch.randn(BATCH_SIZE, seq_len, config.temporal.input_dim)
            out = temporal(x)
            assert out.shape == (BATCH_SIZE, config.temporal.output_dim)

    def test_output_is_finite(self, config):
        temporal = GRUTemporal(config.temporal)
        x = torch.randn(BATCH_SIZE, SEQ_LEN, config.temporal.input_dim)
        out = temporal(x)
        assert torch.isfinite(out).all()
