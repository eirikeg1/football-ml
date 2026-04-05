"""Smoke tests: forward pass through each feature extractor."""

import pytest
import torch

from football_ml.config import (
    MatchContextConfig,
    PlayerFormConfig,
    PlayerProfileConfig,
    TeamPerformanceConfig,
)
from football_ml.feature_extractors import (
    MatchContextEncoder,
    PlayerFormEncoder,
    PlayerProfileEncoder,
    TeamPerformanceEncoder,
)

BATCH_SIZE = 4


@pytest.mark.smoke
class TestPlayerProfileEncoder:
    def test_forward_shape(self, player_profile_input, config):
        cfg = config.feature_extractors.player_profile
        encoder = PlayerProfileEncoder(cfg)
        out = encoder(player_profile_input)
        assert out.shape == (BATCH_SIZE, cfg.output_dim)

    def test_output_is_finite(self, player_profile_input, config):
        encoder = PlayerProfileEncoder(config.feature_extractors.player_profile)
        out = encoder(player_profile_input)
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestPlayerFormEncoder:
    def test_forward_shape(self, player_form_input, config):
        cfg = config.feature_extractors.player_form
        encoder = PlayerFormEncoder(cfg)
        out = encoder(player_form_input)
        assert out.shape == (BATCH_SIZE, cfg.output_dim)

    def test_output_is_finite(self, player_form_input, config):
        encoder = PlayerFormEncoder(config.feature_extractors.player_form)
        out = encoder(player_form_input)
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestTeamPerformanceEncoder:
    def test_forward_shape(self, team_performance_input, config):
        cfg = config.feature_extractors.team_performance
        encoder = TeamPerformanceEncoder(cfg)
        out = encoder(team_performance_input)
        assert out.shape == (BATCH_SIZE, cfg.output_dim)

    def test_output_is_finite(self, team_performance_input, config):
        encoder = TeamPerformanceEncoder(config.feature_extractors.team_performance)
        out = encoder(team_performance_input)
        assert torch.isfinite(out).all()


@pytest.mark.smoke
class TestMatchContextEncoder:
    def test_forward_shape(self, match_context_input, config):
        cfg = config.feature_extractors.match_context
        encoder = MatchContextEncoder(cfg)
        out = encoder(match_context_input)
        assert out.shape == (BATCH_SIZE, cfg.output_dim)

    def test_output_is_finite(self, match_context_input, config):
        encoder = MatchContextEncoder(config.feature_extractors.match_context)
        out = encoder(match_context_input)
        assert torch.isfinite(out).all()
