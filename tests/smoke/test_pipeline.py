"""Smoke test: end-to-end forward pass through the full pipeline."""

import pytest
import torch

from football_ml.config import PipelineConfig
from football_ml.pipeline import FootballPipeline

BATCH_SIZE = 4


@pytest.mark.smoke
class TestFullPipeline:
    def test_match_outcome_forward(self, config, player_profile_input, player_form_input,
                                     team_performance_input, match_context_input,
                                     lineup_batch_pair):
        pipeline = FootballPipeline(config, head="match_outcome")
        home_lineup, away_lineup = lineup_batch_pair
        out = pipeline(
            player_profiles=player_profile_input,
            player_form=player_form_input,
            team_performance=team_performance_input,
            match_context=match_context_input,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            seq_len=5,
        )
        assert out.shape == (BATCH_SIZE, config.heads.match_outcome.num_classes)
        assert torch.isfinite(out).all()

    def test_scoreline_forward(self, config, player_profile_input, player_form_input,
                                team_performance_input, match_context_input,
                                lineup_batch_pair):
        pipeline = FootballPipeline(config, head="scoreline")
        home_lineup, away_lineup = lineup_batch_pair
        out = pipeline(
            player_profiles=player_profile_input,
            player_form=player_form_input,
            team_performance=team_performance_input,
            match_context=match_context_input,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
        )
        assert out.shape == (BATCH_SIZE, 2, config.heads.scoreline.max_goals + 1)

    def test_invalid_head_raises(self, config):
        with pytest.raises(ValueError, match="Unknown head"):
            FootballPipeline(config, head="nonexistent")
