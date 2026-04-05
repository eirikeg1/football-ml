"""Unit tests for base class interface contracts."""

import pytest
import torch
from torch import Tensor, nn

from football_ml.base import (
    CompositionModule,
    FeatureExtractor,
    FusionModule,
    PredictionHead,
    TemporalModule,
)


class TestFeatureExtractorContract:
    def test_cannot_instantiate_without_forward(self):
        """FeatureExtractor subclass must implement forward."""
        class BadExtractor(FeatureExtractor):
            output_dim = 10

        with pytest.raises(TypeError):
            BadExtractor()

    def test_valid_subclass(self):
        class GoodExtractor(FeatureExtractor):
            output_dim = 10
            def forward(self, x):
                return x

        ext = GoodExtractor()
        assert ext.output_dim == 10


class TestFusionModuleContract:
    def test_cannot_instantiate_without_forward(self):
        class BadFusion(FusionModule):
            output_dim = 10

        with pytest.raises(TypeError):
            BadFusion()


class TestTemporalModuleContract:
    def test_cannot_instantiate_without_forward(self):
        class BadTemporal(TemporalModule):
            output_dim = 10

        with pytest.raises(TypeError):
            BadTemporal()


class TestPredictionHeadContract:
    def test_cannot_instantiate_without_forward(self):
        class BadHead(PredictionHead):
            pass

        with pytest.raises(TypeError):
            BadHead()
