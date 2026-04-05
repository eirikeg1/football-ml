"""Smoke tests: forward pass through each prediction head."""

import pytest
import torch

from football_ml.heads import MatchOutcomeHead, MatchStatHead, PlayerStatHead, ScorelineHead

BATCH_SIZE = 4


@pytest.mark.smoke
class TestMatchOutcomeHead:
    def test_forward_shape(self, config):
        cfg = config.heads.match_outcome
        head = MatchOutcomeHead(cfg)
        x = torch.randn(BATCH_SIZE, cfg.input_dim)
        out = head(x)
        assert out.shape == (BATCH_SIZE, cfg.num_classes)

    def test_output_is_finite(self, config):
        cfg = config.heads.match_outcome
        head = MatchOutcomeHead(cfg)
        out = head(torch.randn(BATCH_SIZE, cfg.input_dim))
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestScorelineHead:
    def test_forward_shape(self, config):
        cfg = config.heads.scoreline
        head = ScorelineHead(cfg)
        x = torch.randn(BATCH_SIZE, cfg.input_dim)
        out = head(x)
        assert out.shape == (BATCH_SIZE, 2, cfg.max_goals + 1)

    def test_output_is_finite(self, config):
        cfg = config.heads.scoreline
        head = ScorelineHead(cfg)
        out = head(torch.randn(BATCH_SIZE, cfg.input_dim))
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestPlayerStatHead:
    def test_forward_shape(self, config):
        cfg = config.heads.player_stat
        head = PlayerStatHead(cfg)
        x = torch.randn(BATCH_SIZE, cfg.input_dim)
        out = head(x)
        assert out.shape == (BATCH_SIZE, cfg.num_stats)


@pytest.mark.smoke
class TestMatchStatHead:
    def test_forward_shape(self, config):
        cfg = config.heads.match_stat
        head = MatchStatHead(cfg)
        x = torch.randn(BATCH_SIZE, cfg.input_dim)
        out = head(x)
        assert out.shape == (BATCH_SIZE, cfg.num_stats)
