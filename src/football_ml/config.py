"""Configuration dataclasses and YAML loading."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dacite import from_dict


@dataclass
class PlayerProfileConfig:
    input_dim: int = 50
    hidden_dim: int = 128
    output_dim: int = 64
    num_layers: int = 3


@dataclass
class PlayerFormConfig:
    input_dim: int = 20
    hidden_dim: int = 64
    output_dim: int = 64
    seq_len: int = 10


@dataclass
class TeamPerformanceConfig:
    input_dim: int = 15
    hidden_dim: int = 64
    output_dim: int = 64


@dataclass
class MatchContextConfig:
    input_dim: int = 10
    output_dim: int = 32


@dataclass
class FeatureExtractorsConfig:
    player_profile: PlayerProfileConfig = field(default_factory=PlayerProfileConfig)
    player_form: PlayerFormConfig = field(default_factory=PlayerFormConfig)
    team_performance: TeamPerformanceConfig = field(default_factory=TeamPerformanceConfig)
    match_context: MatchContextConfig = field(default_factory=MatchContextConfig)


@dataclass
class LineupGNNConfig:
    player_dim: int = 128
    hidden_dim: int = 128
    output_dim: int = 64
    num_layers: int = 2


@dataclass
class CompositionConfig:
    lineup_gnn: LineupGNNConfig = field(default_factory=LineupGNNConfig)


@dataclass
class FusionConfig:
    type: str = "transformer"
    d_model: int = 64
    nhead: int = 4
    num_layers: int = 2
    output_dim: int = 128


@dataclass
class TemporalConfig:
    type: str = "gru"
    input_dim: int = 128
    hidden_dim: int = 128
    output_dim: int = 128
    num_layers: int = 1


@dataclass
class MatchOutcomeHeadConfig:
    input_dim: int = 128
    num_classes: int = 3


@dataclass
class ScorelineHeadConfig:
    input_dim: int = 128
    max_goals: int = 10


@dataclass
class PlayerStatHeadConfig:
    input_dim: int = 128
    num_stats: int = 5


@dataclass
class MatchStatHeadConfig:
    input_dim: int = 128
    num_stats: int = 8


@dataclass
class HeadsConfig:
    match_outcome: MatchOutcomeHeadConfig = field(default_factory=MatchOutcomeHeadConfig)
    scoreline: ScorelineHeadConfig = field(default_factory=ScorelineHeadConfig)
    player_stat: PlayerStatHeadConfig = field(default_factory=PlayerStatHeadConfig)
    match_stat: MatchStatHeadConfig = field(default_factory=MatchStatHeadConfig)


@dataclass
class ColumnConfig:
    name: str = ""
    role: str = "feature"  # "feature", "label", "key", "ignore"


@dataclass
class TableConfig:
    name: str = ""
    columns: list[ColumnConfig] = field(default_factory=list)


@dataclass
class RelationshipConfig:
    from_table: str = ""
    from_column: str = ""
    to_table: str = ""
    to_column: str = ""
    rel_type: str = "many_to_one"


@dataclass
class DataSourceConfig:
    type: str = "sqlite"  # "sqlite" | "csv"
    path: str = ""
    tables: list[TableConfig] = field(default_factory=list)
    relationships: list[RelationshipConfig] = field(default_factory=list)


@dataclass
class MaterializationConfig:
    strategy: str = "flatten"  # "flatten" | "aligned" | "heterogeneous_graph"
    join_order: list[str] = field(default_factory=list)
    join_type: str = "inner"
    node_types: list[dict] = field(default_factory=list)
    edge_types: list[dict] = field(default_factory=list)


@dataclass
class PipelineConfig:
    data_sources: list[DataSourceConfig] = field(default_factory=list)
    materialization: MaterializationConfig = field(
        default_factory=MaterializationConfig
    )
    feature_extractors: FeatureExtractorsConfig = field(
        default_factory=FeatureExtractorsConfig
    )
    composition: CompositionConfig = field(default_factory=CompositionConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    heads: HeadsConfig = field(default_factory=HeadsConfig)


def load_config(path: str | Path) -> PipelineConfig:
    """Load a pipeline config from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return from_dict(data_class=PipelineConfig, data=data)
