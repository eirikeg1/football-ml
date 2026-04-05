"""Smoke tests: forward pass through fusion modules."""

import pytest
import torch

from football_ml.config import FusionConfig
from football_ml.fusion import HybridFusion, TransformerFusion

BATCH_SIZE = 4


def _make_embeddings(batch_size: int, dims: list[int]) -> list[torch.Tensor]:
    return [torch.randn(batch_size, d) for d in dims]


@pytest.mark.smoke
class TestTransformerFusion:
    def test_forward_shape(self, config):
        fusion = TransformerFusion(config.fusion)
        embeddings = _make_embeddings(BATCH_SIZE, [64, 32, 64, 64])
        out = fusion(embeddings)
        assert out.shape == (BATCH_SIZE, config.fusion.output_dim)

    def test_variable_token_count(self, config):
        """Fusion should handle different numbers of input tokens."""
        fusion = TransformerFusion(config.fusion)
        # First call with 4 tokens
        embs4 = _make_embeddings(BATCH_SIZE, [64, 32, 64, 64])
        out4 = fusion(embs4)
        assert out4.shape == (BATCH_SIZE, config.fusion.output_dim)

        # Second call with 2 tokens (subset of features)
        embs2 = _make_embeddings(BATCH_SIZE, [64, 32])
        out2 = fusion(embs2)
        assert out2.shape == (BATCH_SIZE, config.fusion.output_dim)

    def test_output_is_finite(self, config):
        fusion = TransformerFusion(config.fusion)
        embeddings = _make_embeddings(BATCH_SIZE, [64, 32, 64])
        out = fusion(embeddings)
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestHybridFusion:
    def test_forward_shape(self, config):
        dims = [64, 32, 64, 64]
        fusion = HybridFusion(config.fusion, group_dims=dims)
        embeddings = _make_embeddings(BATCH_SIZE, dims)
        out = fusion(embeddings)
        assert out.shape == (BATCH_SIZE, config.fusion.output_dim)

    def test_output_is_finite(self, config):
        dims = [64, 32, 64]
        fusion = HybridFusion(config.fusion, group_dims=dims)
        embeddings = _make_embeddings(BATCH_SIZE, dims)
        out = fusion(embeddings)
        assert torch.isfinite(out).all()
