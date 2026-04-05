"""Unit tests for config loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from football_ml.config import PipelineConfig, load_config


class TestPipelineConfigDefaults:
    def test_default_config_has_all_sections(self):
        config = PipelineConfig()
        assert config.feature_extractors is not None
        assert config.composition is not None
        assert config.fusion is not None
        assert config.temporal is not None
        assert config.heads is not None

    def test_default_fusion_type_is_transformer(self):
        config = PipelineConfig()
        assert config.fusion.type == "transformer"

    def test_default_temporal_type_is_gru(self):
        config = PipelineConfig()
        assert config.temporal.type == "gru"


class TestLoadConfig:
    def test_load_from_yaml(self, tmp_path):
        data = {
            "feature_extractors": {
                "player_profile": {"input_dim": 30, "output_dim": 32},
            },
            "fusion": {"type": "transformer", "d_model": 32, "nhead": 2},
        }
        yaml_path = tmp_path / "test_config.yaml"
        yaml_path.write_text(yaml.dump(data))

        config = load_config(yaml_path)
        assert config.feature_extractors.player_profile.input_dim == 30
        assert config.feature_extractors.player_profile.output_dim == 32
        assert config.fusion.d_model == 32

    def test_load_default_yaml(self):
        config_path = Path(__file__).parents[2] / "configs" / "default.yaml"
        if config_path.exists():
            config = load_config(config_path)
            assert config.fusion.type == "transformer"
            assert config.temporal.type == "gru"

    def test_partial_yaml_uses_defaults(self, tmp_path):
        """YAML with partial config should fill in defaults for missing fields."""
        data = {"fusion": {"type": "hybrid"}}
        yaml_path = tmp_path / "partial.yaml"
        yaml_path.write_text(yaml.dump(data))

        config = load_config(yaml_path)
        assert config.fusion.type == "hybrid"
        # Other sections should have defaults
        assert config.feature_extractors.player_profile.input_dim == 50
