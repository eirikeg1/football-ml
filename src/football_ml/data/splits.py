"""Parametric train/val/test split strategies.

Each strategy takes a list of samples + auxiliary frames + params + a seed and
returns three index lists. Strategies are fully deterministic given inputs.
The chosen strategy name and its params are recorded in run_meta.json so any
historical run is reproducible.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import Any

import pandas as pd

# A sample only needs to expose `match_id` and `date_key` for the time-based
# strategies; we keep the signature loose so any sample dataclass works.
SampleLike = Any
SplitIndices = tuple[list[int], list[int], list[int]]
SplitFn = Callable[
    [Sequence[SampleLike], pd.DataFrame, dict[str, Any], int | None], SplitIndices
]


_ONE_DAY_SECS = 86400
_ONE_YEAR_SECS = 365 * _ONE_DAY_SECS


def latest_season_per_competition(
    samples: Sequence[SampleLike],
    matches_df: pd.DataFrame,
    params: dict[str, Any],
    seed: int | None = None,
) -> SplitIndices:
    """Test = most recent ~season per competition. Val = the season before.

    Params:
        test_window_days (int, default 365): seconds-window from each
            competition's max kickoff_time that defines the test set.
        val_window_days (int, default 365): same window backed off by one
            test window for the val set.

    Deterministic; no shuffling involved.
    """
    test_window = int(params.get("test_window_days", 365)) * _ONE_DAY_SECS
    val_window = int(params.get("val_window_days", 365)) * _ONE_DAY_SECS

    if matches_df.empty:
        # Degenerate dataset: fall back to time_percentile so something works.
        return time_percentile(samples, matches_df, params, seed)

    info_by_match: dict[int, tuple[int, int]] = {}
    for row in matches_df[["id", "competition_id", "kickoff_time"]].itertuples(
        index=False
    ):
        info_by_match[int(row.id)] = (int(row.competition_id), int(row.kickoff_time))

    latest_by_comp: dict[int, int] = (
        matches_df.groupby("competition_id")["kickoff_time"].max().astype(int).to_dict()
    )

    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []
    for i, s in enumerate(samples):
        info = info_by_match.get(int(getattr(s, "match_id", -1)))
        if info is None:
            train_idx.append(i)
            continue
        comp, kt = info
        latest = latest_by_comp.get(comp, 0)
        if kt >= latest - test_window:
            test_idx.append(i)
        elif kt >= latest - test_window - val_window:
            val_idx.append(i)
        else:
            train_idx.append(i)
    return train_idx, val_idx, test_idx


def time_percentile(
    samples: Sequence[SampleLike],
    matches_df: pd.DataFrame,
    params: dict[str, Any],
    seed: int | None = None,
) -> SplitIndices:
    """Global time-based split by kickoff_time percentile across all matches.

    Params:
        train_end (float, default 0.7)
        val_end   (float, default 0.85)
    Anything past val_end is test. Sample order is preserved as a tie-breaker.
    """
    train_end = float(params.get("train_end", 0.7))
    val_end = float(params.get("val_end", 0.85))
    if not (0.0 < train_end < val_end < 1.0):
        raise ValueError(
            f"time_percentile requires 0 < train_end < val_end < 1, "
            f"got {train_end=}, {val_end=}"
        )

    # Time key per sample. If matches_df is empty, fall back to sample order.
    if matches_df.empty:
        kt_by_match: dict[int, int] = {}
    else:
        kt_by_match = {
            int(row.id): int(row.kickoff_time)
            for row in matches_df[["id", "kickoff_time"]].itertuples(index=False)
        }

    keyed: list[tuple[int, int]] = []
    for i, s in enumerate(samples):
        mid = int(getattr(s, "match_id", -1))
        kt = kt_by_match.get(mid)
        if kt is None:
            kt = int(getattr(s, "date_key", i))
        keyed.append((kt, i))

    keyed.sort()  # stable, breaks ties by original index
    n = len(keyed)
    train_cut = int(n * train_end)
    val_cut = int(n * val_end)
    train_idx = [i for _, i in keyed[:train_cut]]
    val_idx = [i for _, i in keyed[train_cut:val_cut]]
    test_idx = [i for _, i in keyed[val_cut:]]
    return train_idx, val_idx, test_idx


def season_year(
    samples: Sequence[SampleLike],
    matches_df: pd.DataFrame,
    params: dict[str, Any],
    seed: int | None = None,
) -> SplitIndices:
    """Explicit "test = matches in these seasons" split.

    Params:
        test_seasons (list[int]): season_id values for the test set.
        val_seasons (list[int]): season_id values for the val set.
    Everything else goes to train. Requires a `season_id` column on matches.
    """
    test_seasons = set(int(s) for s in params.get("test_seasons", []))
    val_seasons = set(int(s) for s in params.get("val_seasons", []))
    if not test_seasons:
        raise ValueError("season_year requires non-empty test_seasons")
    if "season_id" not in matches_df.columns:
        raise ValueError(
            "season_year split requires a season_id column on matches; "
            "fall back to time_percentile or latest_season_per_competition"
        )

    season_by_match: dict[int, int] = {
        int(row.id): int(row.season_id)
        for row in matches_df[["id", "season_id"]].itertuples(index=False)
    }

    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []
    for i, s in enumerate(samples):
        season = season_by_match.get(int(getattr(s, "match_id", -1)))
        if season in test_seasons:
            test_idx.append(i)
        elif season in val_seasons:
            val_idx.append(i)
        else:
            train_idx.append(i)
    return train_idx, val_idx, test_idx


def random_seeded(
    samples: Sequence[SampleLike],
    matches_df: pd.DataFrame,
    params: dict[str, Any],
    seed: int | None = None,
) -> SplitIndices:
    """Time-blind random split with a fixed seed.

    For ablation only — leaks future information into train. The split itself
    is reproducible given the seed. Use with care.

    Params:
        train_frac (float, default 0.7)
        val_frac   (float, default 0.15)
    """
    train_frac = float(params.get("train_frac", 0.7))
    val_frac = float(params.get("val_frac", 0.15))
    if seed is None:
        seed = 0  # still deterministic, but warn at the call site

    indices = list(range(len(samples)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    n = len(indices)
    train_cut = int(n * train_frac)
    val_cut = int(n * (train_frac + val_frac))
    return indices[:train_cut], indices[train_cut:val_cut], indices[val_cut:]


STRATEGIES: dict[str, SplitFn] = {
    "latest_season_per_competition": latest_season_per_competition,
    "time_percentile": time_percentile,
    "season_year": season_year,
    "random_seeded": random_seeded,
}


def make_split(
    strategy: str,
    samples: Sequence[SampleLike],
    matches_df: pd.DataFrame,
    params: dict[str, Any] | None = None,
    seed: int | None = None,
) -> SplitIndices:
    """Dispatch to a named split strategy.

    Raises ValueError if the strategy is unknown.
    """
    fn = STRATEGIES.get(strategy)
    if fn is None:
        known = ", ".join(sorted(STRATEGIES))
        raise ValueError(f"Unknown split strategy {strategy!r}. Known: {known}")
    return fn(samples, matches_df, params or {}, seed)
