"""Shared test fixtures."""

import pytest
import torch
from torch_geometric.data import Batch, Data

from football_ml.config import (
    CompositionConfig,
    FeatureExtractorsConfig,
    FusionConfig,
    HeadsConfig,
    LineupGNNConfig,
    MatchContextConfig,
    MatchOutcomeHeadConfig,
    MatchStatHeadConfig,
    PipelineConfig,
    PlayerFormConfig,
    PlayerProfileConfig,
    PlayerStatHeadConfig,
    ScorelineHeadConfig,
    TeamPerformanceConfig,
    TemporalConfig,
)

BATCH_SIZE = 4
SEQ_LEN = 5
PLAYERS_PER_TEAM = 11


@pytest.fixture
def config() -> PipelineConfig:
    """Default pipeline config for testing."""
    return PipelineConfig()


@pytest.fixture
def player_profile_input() -> torch.Tensor:
    return torch.randn(BATCH_SIZE, 50)


@pytest.fixture
def player_form_input() -> torch.Tensor:
    return torch.randn(BATCH_SIZE, SEQ_LEN, 20)


@pytest.fixture
def team_performance_input() -> torch.Tensor:
    return torch.randn(BATCH_SIZE, 15)


@pytest.fixture
def match_context_input() -> torch.Tensor:
    return torch.randn(BATCH_SIZE, 10)


def _make_lineup_graph(player_dim: int) -> Data:
    """Create a single lineup graph with 11 players in a chain topology."""
    x = torch.randn(PLAYERS_PER_TEAM, player_dim)
    # Simple chain connectivity: 0-1, 1-2, ..., 9-10
    src = list(range(PLAYERS_PER_TEAM - 1))
    dst = list(range(1, PLAYERS_PER_TEAM))
    edge_index = torch.tensor([src + dst, dst + src], dtype=torch.long)
    return Data(x=x, edge_index=edge_index)


@pytest.fixture
def lineup_batch() -> Batch:
    """Batched lineup graphs for testing GNN."""
    graphs = [_make_lineup_graph(player_dim=128) for _ in range(BATCH_SIZE)]
    return Batch.from_data_list(graphs)


@pytest.fixture
def lineup_batch_pair() -> tuple[Batch, Batch]:
    """Home and away lineup batches for pipeline testing."""
    home = [_make_lineup_graph(player_dim=128) for _ in range(BATCH_SIZE)]
    away = [_make_lineup_graph(player_dim=128) for _ in range(BATCH_SIZE)]
    return Batch.from_data_list(home), Batch.from_data_list(away)
