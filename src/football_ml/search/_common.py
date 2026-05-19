"""Shared utilities for the search-loop helpers (leaderboard / report / multi-seed).

All helpers operate on the directory layout the goal-search skill creates:

    results/<search>/
        baseline.yaml
        runs/iter-XXX/
            config.yaml
            status.json
            metrics.jsonl
            ...
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml


def iter_run_dirs(results_dir: Path) -> Iterator[Path]:
    runs = results_dir / "runs"
    if not runs.exists():
        return iter(())
    return iter(sorted(p for p in runs.iterdir() if p.is_dir()))


def load_status(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "status.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def load_metrics(run_dir: Path) -> list[dict[str, Any]]:
    p = run_dir / "metrics.jsonl"
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_config(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "config.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def load_baseline(results_dir: Path) -> dict[str, Any]:
    p = results_dir / "baseline.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def diff_configs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a flat dict of {dotted.key: (baseline_val, candidate_val)} for differences.

    Walks both nested dicts; cares only about leaf values. Missing keys on either
    side appear as (None, value) or (value, None).
    """
    diff: dict[str, Any] = {}
    _walk_diff("", baseline, candidate, diff)
    return diff


def _walk_diff(prefix: str, b: Any, c: Any, out: dict[str, Any]) -> None:
    if isinstance(b, dict) or isinstance(c, dict):
        bd = b if isinstance(b, dict) else {}
        cd = c if isinstance(c, dict) else {}
        for k in sorted(set(bd) | set(cd)):
            _walk_diff(f"{prefix}.{k}" if prefix else k, bd.get(k), cd.get(k), out)
        return
    if b != c:
        out[prefix] = (b, c)


def summarize_delta(diff: dict[str, Any]) -> str:
    """Compact one-liner describing the meaningful diffs (skips noisy keys)."""
    skip_keys = {"position", "config"}  # YAML position arrays and detail configs are noisy
    parts: list[str] = []
    for k, (b, c) in diff.items():
        if any(s in k for s in skip_keys):
            continue
        parts.append(f"{k}: {b!r}→{c!r}")
    return ", ".join(parts) or "(no changes)"


def primary_metric_from_status(status: dict[str, Any]) -> float | None:
    """Best val metric if recorded, else None."""
    v = status.get("best_metric")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
