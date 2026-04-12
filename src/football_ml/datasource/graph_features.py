"""Feature encoding for heterogeneous graph node types."""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import Tensor

# Canonical event types for one-hot encoding
EVENT_TYPES = [
    "goal",
    "yellow_card",
    "red_card",
    "second_yellow",
    "substitution",
    "penalty",
    "own_goal",
]

_EVENT_TO_IDX = {e: i for i, e in enumerate(EVENT_TYPES)}


def encode_match_features(matches_df: pd.DataFrame) -> Tensor:
    """Encode match-level numeric features.

    Features: matchday (normalized), kickoff_time (normalized),
    home_score, away_score.

    For target matches (future), home_score and away_score should be
    set to 0 or NaN before calling this.

    Returns:
        Tensor of shape (num_matches, 4).
    """
    df = matches_df.copy()

    # Normalize kickoff_time to [0, 1] range within the dataset
    if "kickoff_time" in df.columns:
        kt = df["kickoff_time"].astype(float)
        kt_min, kt_max = kt.min(), kt.max()
        if kt_max > kt_min:
            df["kickoff_norm"] = (kt - kt_min) / (kt_max - kt_min)
        else:
            df["kickoff_norm"] = 0.0
    else:
        df["kickoff_norm"] = 0.0

    # Normalize matchday
    if "matchday" in df.columns:
        md = df["matchday"].fillna(0).astype(float)
        md_max = md.max()
        df["matchday_norm"] = md / md_max if md_max > 0 else 0.0
    else:
        df["matchday_norm"] = 0.0

    features = df[["matchday_norm", "kickoff_norm"]].copy()

    for col in ["home_score", "away_score"]:
        if col in df.columns:
            features[col] = df[col].fillna(0).astype(float)
        else:
            features[col] = 0.0

    return torch.tensor(features.values, dtype=torch.float32)


def encode_match_stat_features(stats_df: pd.DataFrame) -> Tensor:
    """Encode match_stats numeric features.

    Uses all stat columns: possession, pass_accuracy, total_passes,
    shots, shots_on_target, corners, fouls, yellow_cards, red_cards,
    offsides, saves.

    Returns:
        Tensor of shape (num_stats, 11).
    """
    stat_cols = [
        "possession",
        "pass_accuracy",
        "total_passes",
        "shots",
        "shots_on_target",
        "corners",
        "fouls",
        "yellow_cards",
        "red_cards",
        "offsides",
        "saves",
    ]
    cols = [c for c in stat_cols if c in stats_df.columns]
    if not cols:
        return torch.zeros((len(stats_df), 1), dtype=torch.float32)

    values = stats_df[cols].fillna(0).values.astype(np.float32)
    return torch.tensor(values, dtype=torch.float32)


def encode_event_features(events_df: pd.DataFrame) -> Tensor:
    """Encode match_event features: minute + extra_minute + one-hot event_type.

    Returns:
        Tensor of shape (num_events, 9).  [minute, extra_minute, 7x one-hot]
    """
    n = len(events_df)
    features = np.zeros((n, 2 + len(EVENT_TYPES)), dtype=np.float32)

    if "minute" in events_df.columns:
        features[:, 0] = events_df["minute"].fillna(0).values / 90.0  # normalize
    if "extra_minute" in events_df.columns:
        features[:, 1] = events_df["extra_minute"].fillna(0).values / 15.0

    if "event_type" in events_df.columns:
        for i, etype in enumerate(events_df["event_type"].values):
            idx = _EVENT_TO_IDX.get(etype)
            if idx is not None:
                features[i, 2 + idx] = 1.0

    return torch.tensor(features, dtype=torch.float32)


def aggregate_events(
    events_df: pd.DataFrame,
    match_stats_df: pd.DataFrame,
) -> pd.DataFrame:
    """Pre-aggregate events into per-team per-match counts.

    Computes: goals, yellow_cards, red_cards, second_yellows,
    substitutions, penalties, own_goals per (match_id, team_id).

    Merges these as extra columns onto match_stats_df.

    Returns:
        Updated match_stats DataFrame with event count columns appended.
    """
    if events_df.empty:
        for et in EVENT_TYPES:
            match_stats_df[f"evt_{et}"] = 0
        return match_stats_df

    # Pivot event counts
    counts = (
        events_df.groupby(["match_id", "team_id", "event_type"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Ensure all event type columns exist
    for et in EVENT_TYPES:
        if et not in counts.columns:
            counts[et] = 0

    # Rename to avoid collision with existing stat columns
    rename = {et: f"evt_{et}" for et in EVENT_TYPES}
    counts = counts.rename(columns=rename)

    evt_cols = ["match_id", "team_id"] + [f"evt_{et}" for et in EVENT_TYPES]
    counts = counts[evt_cols]

    result = match_stats_df.merge(counts, on=["match_id", "team_id"], how="left")
    for col in [f"evt_{et}" for et in EVENT_TYPES]:
        result[col] = result[col].fillna(0).astype(int)

    return result
