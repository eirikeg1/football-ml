"""Capture per-run reproducibility metadata.

Written once at the start of every training run as `run_meta.json` inside the
run directory. Goal: months from now, given the run dir alone, we can
re-run the same config on the same data.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


def _git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        ).stdout.strip()
        return out or None
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return None


def _git_dirty() -> bool | None:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        ).stdout
        return bool(out.strip())
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return None


def _library_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    for pkg in ("torch", "torch_geometric", "numpy", "pandas", "pyyaml"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[pkg] = "missing"
    return versions


def _dataset_snapshot(db_path: str | None) -> dict[str, Any]:
    """Capture a fingerprint of the dataset state (latest match in DB)."""
    if not db_path:
        return {}
    p = Path(db_path).expanduser()
    if not p.exists():
        return {"db_path": str(p), "exists": False}
    info: dict[str, Any] = {
        "db_path": str(p),
        "exists": True,
        "file_size_bytes": p.stat().st_size,
        "file_mtime": p.stat().st_mtime,
    }
    try:
        with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(kickoff_time), COUNT(*) FROM matches")
            row = cur.fetchone()
            if row is not None:
                info["max_kickoff_time"] = row[0]
                info["match_count"] = row[1]
    except sqlite3.Error as e:
        info["sqlite_error"] = str(e)
    return info


def write_run_meta(
    run_dir: Path | str,
    *,
    cli_args: list[str],
    config: dict[str, Any],
    db_path: str | None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write `<run_dir>/run_meta.json` and return its path."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "start_time": time.time(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "platform": platform.platform(),
        "cli_args": cli_args,
        "git_sha": _git_sha(),
        "git_dirty": _git_dirty(),
        "library_versions": _library_versions(),
        "dataset": _dataset_snapshot(db_path),
        "config": config,
    }
    if extra:
        meta.update(extra)
    path = run_dir / "run_meta.json"
    path.write_text(json.dumps(meta, indent=2, default=str))
    return path


def append_run_meta(run_dir: Path | str, patch: dict[str, Any]) -> None:
    """Merge a patch into an existing run_meta.json (e.g., end_time, exit_code)."""
    run_dir = Path(run_dir)
    path = run_dir / "run_meta.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        data = {}
    data.update(patch)
    path.write_text(json.dumps(data, indent=2, default=str))
