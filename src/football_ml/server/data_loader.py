"""Load real training data from pipeline YAML configuration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import torch
from torch import Tensor

from football_ml.datasource.base import RelationshipMeta
from football_ml.datasource.sqlite_source import SqliteSource
from football_ml.datasource.snapshot import SnapshotBuilder, TrainingSample
from football_ml.config import HeteroGNNConfig, SnapshotConfig
from football_ml.training.config import TrainingConfig


def _parse_pipeline_yaml(pipeline_data: dict) -> tuple[str | None, dict | None]:
    """Extract SQLite source config from parsed pipeline YAML.

    Returns:
        Tuple of (db_path, source_config_dict) or (None, None) if not found.
    """
    nodes = pipeline_data.get("nodes", {})
    for node_id, node in nodes.items():
        if node.get("type") == "sqlite_source":
            config = node.get("config", {})
            db_path = config.get("dbPath") or node.get("params", {}).get("db_path")
            if db_path:
                return db_path, config
    return None, None


def _has_hetero_gnn(pipeline_data: dict) -> bool:
    """Check if the pipeline graph contains a hetero_gnn node."""
    nodes = pipeline_data.get("nodes", {})
    return any(n.get("type") == "hetero_gnn" for n in nodes.values())


def _parse_relationships(config: dict) -> list[RelationshipMeta]:
    """Convert relationship dicts from YAML config to RelationshipMeta."""
    rels = []
    for r in config.get("relationships", []):
        rels.append(RelationshipMeta(
            from_table=r["fromTable"],
            from_column=r["fromColumn"],
            to_table=r["toTable"],
            to_column=r["toColumn"],
            rel_type=r.get("type", "many_to_one"),
        ))
    return rels


def _get_head_type(pipeline_data: dict) -> str:
    """Find the first prediction head node type in the pipeline."""
    head_types = {"match_outcome", "scoreline", "player_stat", "match_stat"}
    nodes = pipeline_data.get("nodes", {})
    for node in nodes.values():
        if node.get("type") in head_types:
            return node["type"]
    return "match_outcome"


def load_hetero_data(
    db_path: str,
    source_config: dict,
    training_config: TrainingConfig,
    log: Callable[[str, str], None] | None = None,
) -> tuple[list[dict], list[dict], tuple, int, int]:
    """Load data for HeteroGNN training.

    Returns:
        (train_batches, val_batches, metadata, num_teams, num_competitions)
        Each batch is a dict with "inputs" and "targets" keys.
    """
    _log = log or (lambda l, m: None)

    src = SqliteSource(db_path)
    schema = src.introspect()

    # Filter to included tables from config
    included_names = set()
    for t in source_config.get("tables", []):
        if t.get("included", True):
            included_names.add(t["name"])

    # Always include core tables
    included_names |= {"matches", "match_stats", "teams", "competitions"}

    schema.tables = [t for t in schema.tables if t.name in included_names]
    schema.relationships = [
        r for r in schema.relationships
        if r.from_table in included_names and r.to_table in included_names
    ]

    # Use relationships from config if provided, otherwise from schema
    config_rels = _parse_relationships(source_config)
    if config_rels:
        schema.relationships = config_rels

    _log("info", f"Loading tables: {[t.name for t in schema.tables]}")
    tables = src.load_tables(schema)

    for name, df in tables.items():
        _log("info", f"  {name}: {len(df)} rows")

    num_teams = len(tables.get("teams", pd.DataFrame()))
    num_competitions = len(tables.get("competitions", pd.DataFrame()))

    _log("info", f"Teams: {num_teams}, Competitions: {num_competitions}")

    # Build snapshots
    snapshot_config = SnapshotConfig(
        min_history_matches=20,
        seq_len=training_config.batch_size,
    )
    hetero_config = HeteroGNNConfig(include_events=False)

    _log("info", "Building training samples with rolling snapshots...")
    builder = SnapshotBuilder(
        tables, schema.relationships,
        snapshot_config=snapshot_config,
        hetero_config=hetero_config,
    )

    samples = builder.build_training_samples()
    _log("info", f"Total training samples: {len(samples)}")

    if not samples:
        raise ValueError("No training samples could be created. Check data filters.")

    # Get metadata from the first snapshot
    metadata = samples[0].metadata

    # Time-based split: last val_split fraction for validation
    split_idx = int(len(samples) * (1 - training_config.val_split))
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]

    _log("info", f"Train: {len(train_samples)} samples, Val: {len(val_samples)} samples")

    # Group samples by snapshot date — one GNN forward pass per unique date
    from collections import defaultdict

    def make_batches(sample_list: list[TrainingSample]) -> list[dict]:
        groups: dict[int, list[TrainingSample]] = defaultdict(list)
        for s in sample_list:
            groups[s.date_key].append(s)

        batches = []
        for date_key in sorted(groups.keys()):
            chunk = groups[date_key]
            if len(chunk) < 2:
                continue  # skip single-sample batches (BatchNorm needs >=2)

            snapshot = chunk[0].snapshot
            home_idx = torch.tensor([s.home_team_idx for s in chunk], dtype=torch.long)
            away_idx = torch.tensor([s.away_team_idx for s in chunk], dtype=torch.long)

            outcomes = []
            for s in chunk:
                if s.home_score > s.away_score:
                    outcomes.append(0)
                elif s.home_score == s.away_score:
                    outcomes.append(1)
                else:
                    outcomes.append(2)

            targets: dict[str, Tensor] = {
                "match_outcome": torch.tensor(outcomes, dtype=torch.long),
                "scoreline": torch.tensor(
                    [[s.home_score, s.away_score] for s in chunk], dtype=torch.long,
                ),
                "match_stat": torch.zeros(len(chunk), 8),
            }

            batches.append({
                "inputs": {
                    "data": snapshot,
                    "home_team_idx": home_idx,
                    "away_team_idx": away_idx,
                },
                "targets": targets,
            })

        return batches

    train_batches = make_batches(train_samples)
    val_batches = make_batches(val_samples)

    _log("info", f"Train batches: {len(train_batches)}, Val batches: {len(val_batches)}")

    # Collect actual feature dims from a representative snapshot (use a
    # middle batch where all node types have real data, not the first
    # which may be a tiny early-season graph with empty tables)
    feature_dims: dict[str, int] = {}
    mid_idx = len(train_batches) // 2
    sample_data = train_batches[mid_idx]["inputs"]["data"]
    for nt in sample_data.node_types:
        if hasattr(sample_data[nt], "x"):
            feature_dims[nt] = sample_data[nt].x.shape[1]

    _log("info", f"Node feature dims: {feature_dims}")

    return train_batches, val_batches, metadata, num_teams, num_competitions, feature_dims


def load_flat_data(
    db_path: str,
    source_config: dict,
    training_config: TrainingConfig,
    log: Callable[[str, str], None] | None = None,
    rolling_window: int = 10,
    min_history: int = 5,
) -> tuple[list[dict], list[dict], int]:
    """Load flattened data for the standard FootballPipeline.

    Uses **rolling historical averages** of each team's stats from their
    last N matches as features.  The current match's own stats are never
    used as input — only as the prediction target — to avoid data leakage.

    Feature vector per sample:
        [home_team_rolling_stats | away_team_rolling_stats |
         home_advantage | home_rest_days | away_rest_days |
         home_h2h_win_rate | draw_rate | away_h2h_win_rate]

    Returns:
        (train_batches, val_batches, feature_dim_per_team)
    """
    import numpy as np

    _log = log or (lambda l, m: None)

    src = SqliteSource(db_path)
    schema = src.introspect()

    keep = {"matches", "match_stats", "teams", "competitions"}
    schema.tables = [t for t in schema.tables if t.name in keep]
    tables = src.load_tables(schema)

    matches = tables["matches"]
    match_stats_df = tables.get("match_stats", pd.DataFrame())

    # Finished matches with scores, sorted by time
    matches = matches[matches["status"] == "finished"].copy()
    matches = matches.dropna(subset=["home_score", "away_score"])
    matches = matches.sort_values("kickoff_time").reset_index(drop=True)

    _log("info", f"Finished matches: {len(matches)}")

    stat_cols = [
        "possession", "shots", "shots_on_target", "fouls",
        "corners", "yellow_cards", "red_cards",
    ]
    # Only use columns that exist AND have actual data (not all-null)
    available_stat_cols = [
        c for c in stat_cols
        if c in match_stats_df.columns and match_stats_df[c].notna().sum() > 100
    ]

    if match_stats_df.empty or not available_stat_cols:
        raise ValueError("No match_stats data available for training")

    _log("info", f"Stat features ({len(available_stat_cols)}): {available_stat_cols}")

    # ── Build per-team-per-match stat rows with match kickoff time ───
    team_match_stats = match_stats_df.merge(
        matches[["id", "kickoff_time"]],
        left_on="match_id",
        right_on="id",
        suffixes=("", "_match"),
    ).sort_values("kickoff_time")

    # ── Compute rolling historical averages per team ─────────────────
    # shift(1) ensures we never include the current match's own stats
    _log("info", f"Computing rolling averages (window={rolling_window}, min_history={min_history})...")

    rolling_cols = [f"roll_{c}" for c in available_stat_cols]

    team_match_stats[rolling_cols] = (
        team_match_stats
        .groupby("team_id")[available_stat_cols]
        .transform(
            lambda x: x.shift(1).rolling(rolling_window, min_periods=min_history).mean()
        )
    )

    # Build lookup: (match_id, team_id) → rolling averages
    rolling_lookup: dict[tuple[int, int], list[float]] = {}
    for _, row in team_match_stats.dropna(subset=rolling_cols).iterrows():
        key = (int(row["match_id"]), int(row["team_id"]))
        rolling_lookup[key] = [float(row[c]) for c in rolling_cols]

    _log("info", f"Rolling lookup entries: {len(rolling_lookup)}")

    # ── Compute rest days per team ───────────────────────────────────
    # For each team's match, days since their previous match
    team_match_times: dict[int, list[int]] = {}
    rest_lookup: dict[tuple[int, int], float] = {}

    for _, row in team_match_stats.iterrows():
        tid = int(row["team_id"])
        mid = int(row["match_id"])
        kt = int(row["kickoff_time"])
        prev_times = team_match_times.get(tid, [])
        if prev_times:
            rest_days = (kt - prev_times[-1]) / 86400.0
            rest_lookup[(mid, tid)] = min(rest_days, 30.0) / 30.0  # normalize, cap at 30
        else:
            rest_lookup[(mid, tid)] = 0.5  # unknown → neutral
        if tid not in team_match_times:
            team_match_times[tid] = []
        team_match_times[tid].append(kt)

    # ── Compute head-to-head record ──────────────────────────────────
    h2h_record: dict[tuple[int, int], list[int]] = {}  # (teamA, teamB) → [wins, draws, losses]

    # ── Assemble feature vectors ─────────────────────────────────────
    feature_rows = []
    label_rows = []
    n_stats = len(available_stat_cols)

    for _, match in matches.iterrows():
        match_id = int(match["id"])
        home_id = int(match["home_team_id"])
        away_id = int(match["away_team_id"])

        home_key = (match_id, home_id)
        away_key = (match_id, away_id)

        # Skip if no rolling history for either team
        if home_key not in rolling_lookup or away_key not in rolling_lookup:
            continue

        home_rolling = rolling_lookup[home_key]
        away_rolling = rolling_lookup[away_key]
        home_rest = rest_lookup.get(home_key, 0.5)
        away_rest = rest_lookup.get(away_key, 0.5)

        # Head-to-head running record
        h2h_key = (min(home_id, away_id), max(home_id, away_id))
        record = h2h_record.get(h2h_key, [0, 0, 0])  # [home_wins, draws, away_wins]
        total_h2h = max(sum(record), 1)
        h2h_features = [r / total_h2h for r in record]  # normalize to rates

        # Feature vector
        features = (
            home_rolling          # home team rolling stats
            + away_rolling        # away team rolling stats
            + [1.0]               # home advantage flag
            + [home_rest]         # home team rest days (normalized)
            + [away_rest]         # away team rest days (normalized)
            + h2h_features        # h2h win/draw/loss rates
        )
        feature_rows.append(features)

        # Label
        hs = int(match["home_score"])
        as_ = int(match["away_score"])
        if hs > as_:
            outcome = 0  # home win
        elif hs == as_:
            outcome = 1  # draw
        else:
            outcome = 2  # away win
        label_rows.append(outcome)

        # Update h2h record for future matches
        if outcome == 0:
            record[0] += 1
        elif outcome == 1:
            record[1] += 1
        else:
            record[2] += 1
        h2h_record[h2h_key] = record

    feat_dim = len(feature_rows[0]) if feature_rows else 0
    _log("info", f"Samples with history: {len(feature_rows)}, feature dim: {feat_dim}")
    _log("info", f"  {n_stats} rolling stats x 2 teams + 1 home + 2 rest + 3 h2h = {feat_dim}")

    if not feature_rows:
        raise ValueError("No matches with sufficient history found")

    features_tensor = torch.tensor(feature_rows, dtype=torch.float32)
    labels_tensor = torch.tensor(label_rows, dtype=torch.long)

    # Normalize features (z-score on training set)
    split_idx = int(len(features_tensor) * (1 - training_config.val_split))
    train_mean = features_tensor[:split_idx].mean(dim=0)
    train_std = features_tensor[:split_idx].std(dim=0).clamp(min=1e-6)
    features_tensor = (features_tensor - train_mean) / train_std

    train_x, val_x = features_tensor[:split_idx], features_tensor[split_idx:]
    train_y, val_y = labels_tensor[:split_idx], labels_tensor[split_idx:]

    _log("info", f"Train: {len(train_x)}, Val: {len(val_x)}")

    # Label distribution
    for split_name, labels in [("Train", train_y), ("Val", val_y)]:
        counts = torch.bincount(labels, minlength=3)
        total = len(labels)
        _log("info", f"  {split_name} labels: home_win={counts[0]} ({counts[0]*100//total}%), "
             f"draw={counts[1]} ({counts[1]*100//total}%), away_win={counts[2]} ({counts[2]*100//total}%)")

    # ── Create batches ───────────────────────────────────────────────
    total_feat_dim = features_tensor.shape[1]

    def make_batches(x: Tensor, y: Tensor, batch_size: int) -> list[dict]:
        batches = []
        for i in range(0, len(x), batch_size):
            bx = x[i : i + batch_size]
            by = y[i : i + batch_size]
            if len(bx) < 2:
                continue  # skip incomplete batches (BatchNorm needs ≥2)
            batches.append({
                "inputs": {"features": bx},
                "targets": {"match_outcome": by},
            })
        return batches

    batch_size = training_config.batch_size
    train_batches = make_batches(train_x, train_y, batch_size)
    val_batches = make_batches(val_x, val_y, batch_size)

    _log("info", f"Train batches: {len(train_batches)}, Val batches: {len(val_batches)}")

    return train_batches, val_batches, total_feat_dim


def _make_dummy_lineup(batch_size: int):
    """Create a dummy lineup batch (11 players, chain edges)."""
    from torch_geometric.data import Batch, Data

    src = list(range(10)) + list(range(1, 11))
    dst = list(range(1, 11)) + list(range(10))
    edge_index = torch.tensor([src, dst], dtype=torch.long)

    graphs = [
        Data(x=torch.zeros(11, 128), edge_index=edge_index)
        for _ in range(batch_size)
    ]
    return Batch.from_data_list(graphs)
