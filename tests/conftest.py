"""Shared test fixtures."""

import pytest
import torch
from torch_geometric.data import Batch, Data, HeteroData

from football_ml.config import (
    CompositionConfig,
    FeatureExtractorsConfig,
    FusionConfig,
    HeadsConfig,
    HeteroGNNConfig,
    LineupGNNConfig,
    MatchContextConfig,
    MatchOutcomeHeadConfig,
    MatchStatHeadConfig,
    PipelineConfig,
    PlayerFormConfig,
    PlayerProfileConfig,
    PlayerStatHeadConfig,
    ScorelineHeadConfig,
    SnapshotConfig,
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


# ── HeteroGNN fixtures ─────────────────────────────────────────────

NUM_TEAMS = 4
NUM_COMPETITIONS = 1
NUM_MATCHES = 6
NUM_STATS = 12  # 2 per match


def _build_sample_hetero_data() -> tuple[HeteroData, tuple]:
    """Build a small synthetic HeteroData for testing HeteroGNN."""
    data = HeteroData()

    # Node features
    data["matches"].x = torch.randn(NUM_MATCHES, 4)
    data["matches"].num_nodes = NUM_MATCHES
    data["matches"].node_id = torch.arange(NUM_MATCHES)

    data["match_stats"].x = torch.randn(NUM_STATS, 11)
    data["match_stats"].num_nodes = NUM_STATS
    data["match_stats"].node_id = torch.arange(NUM_STATS)

    data["teams"].x = torch.zeros(NUM_TEAMS, 1)
    data["teams"].num_nodes = NUM_TEAMS
    data["teams"].node_id = torch.arange(NUM_TEAMS)

    data["competitions"].x = torch.zeros(NUM_COMPETITIONS, 1)
    data["competitions"].num_nodes = NUM_COMPETITIONS
    data["competitions"].node_id = torch.arange(NUM_COMPETITIONS)

    # Edge types: match_stats → matches (stat_of)
    stat_src = list(range(NUM_STATS))
    stat_dst = [i // 2 for i in range(NUM_STATS)]  # 2 stats per match
    data["match_stats", "match_id_to_id", "matches"].edge_index = torch.tensor(
        [stat_src, stat_dst], dtype=torch.long
    )
    data["matches", "rev_match_id_to_id", "match_stats"].edge_index = torch.tensor(
        [stat_dst, stat_src], dtype=torch.long
    )

    # match_stats → teams (by_team)
    stat_team = [i % NUM_TEAMS for i in range(NUM_STATS)]
    data["match_stats", "team_id_to_id", "teams"].edge_index = torch.tensor(
        [stat_src, stat_team], dtype=torch.long
    )
    data["teams", "rev_team_id_to_id", "match_stats"].edge_index = torch.tensor(
        [stat_team, stat_src], dtype=torch.long
    )

    # matches → teams (home_team)
    match_src = list(range(NUM_MATCHES))
    home_teams = [i % NUM_TEAMS for i in range(NUM_MATCHES)]
    data["matches", "home_team_id_to_id", "teams"].edge_index = torch.tensor(
        [match_src, home_teams], dtype=torch.long
    )
    data["teams", "rev_home_team_id_to_id", "matches"].edge_index = torch.tensor(
        [home_teams, match_src], dtype=torch.long
    )

    # matches → teams (away_team)
    away_teams = [(i + 1) % NUM_TEAMS for i in range(NUM_MATCHES)]
    data["matches", "away_team_id_to_id", "teams"].edge_index = torch.tensor(
        [match_src, away_teams], dtype=torch.long
    )
    data["teams", "rev_away_team_id_to_id", "matches"].edge_index = torch.tensor(
        [away_teams, match_src], dtype=torch.long
    )

    # matches → competitions
    comp_dst = [0] * NUM_MATCHES
    data["matches", "competition_id_to_id", "competitions"].edge_index = torch.tensor(
        [match_src, comp_dst], dtype=torch.long
    )
    data["competitions", "rev_competition_id_to_id", "matches"].edge_index = torch.tensor(
        [comp_dst, match_src], dtype=torch.long
    )

    node_types = ["matches", "match_stats", "teams", "competitions"]
    edge_types = list(data.edge_types)
    metadata = (node_types, edge_types)

    return data, metadata


@pytest.fixture
def sample_hetero_data() -> tuple[HeteroData, tuple]:
    """Small synthetic HeteroData + metadata for testing HeteroGNN."""
    return _build_sample_hetero_data()


@pytest.fixture
def hetero_config() -> PipelineConfig:
    """Pipeline config tuned for HeteroGNN testing (small dims)."""
    return PipelineConfig(
        composition=CompositionConfig(
            hetero_gnn=HeteroGNNConfig(
                d_model=32,
                num_heads=4,
                num_layers=2,
                dropout=0.0,
                readout_dim=64,
            ),
        ),
        temporal=TemporalConfig(
            input_dim=64,  # matches readout_dim
            hidden_dim=32,
            output_dim=32,
        ),
        heads=HeadsConfig(
            match_outcome=MatchOutcomeHeadConfig(input_dim=32, num_classes=3),
            scoreline=ScorelineHeadConfig(input_dim=32, max_goals=10),
            match_stat=MatchStatHeadConfig(input_dim=32, num_stats=8),
        ),
    )
