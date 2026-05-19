"""Multi-seed validation for a single iteration's config.

Re-runs the config from `<iter-dir>/config.yaml` N times with distinct seeds,
each into its own subdirectory under `<results-dir>/multi-seed/<iter-id>/seed-K/`.
Aggregates the headline metric (val best_metric) into a `summary.json`.

Usage:
    python -m football_ml.search.multi_seed \\
        <results-dir>/runs/iter-007 \\
        --seeds 3 \\
        [--smoke]
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _run_one(
    config_path: Path,
    run_dir: Path,
    seed: int,
    smoke: bool,
    extra_args: list[str],
) -> dict[str, Any]:
    cmd = [
        sys.executable, "-m", "football_ml.cli.train",
        "--config", str(config_path),
        "--run-dir", str(run_dir),
        "--seed", str(seed),
        *(["--smoke"] if smoke else []),
        *extra_args,
    ]
    proc = subprocess.run(cmd)
    status_path = run_dir / "status.json"
    if not status_path.exists():
        return {"seed": seed, "ok": False, "best_metric": None, "exit_code": proc.returncode}
    try:
        status = json.loads(status_path.read_text())
    except json.JSONDecodeError:
        status = {}
    return {
        "seed": seed,
        "ok": status.get("finished") and status.get("exit_code") == 0,
        "best_metric": status.get("best_metric"),
        "exit_code": status.get("exit_code"),
        "epochs_run": status.get("epochs_run"),
        "phase": status.get("phase"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="football-ml-multi-seed")
    p.add_argument("iter_dir", help="Existing iter directory whose config to re-run.")
    p.add_argument("--seeds", type=int, default=3, help="Number of seeded re-runs.")
    p.add_argument("--start-seed", type=int, default=100)
    p.add_argument("--smoke", action="store_true")
    p.add_argument(
        "--passthrough",
        nargs=argparse.REMAINDER,
        help="Args after `--` are forwarded verbatim to football-ml-train.",
    )
    args = p.parse_args(argv)

    iter_dir = Path(args.iter_dir).expanduser().resolve()
    config_path = iter_dir / "config.yaml"
    if not config_path.exists():
        sys.stderr.write(f"No config.yaml in {iter_dir}\n")
        return 2

    # Output: <results-dir>/multi-seed/<iter-id>/seed-K/
    results_dir = iter_dir.parent.parent
    out_root = results_dir / "multi-seed" / iter_dir.name
    out_root.mkdir(parents=True, exist_ok=True)

    extra = args.passthrough or []
    rows: list[dict[str, Any]] = []
    for k in range(args.seeds):
        seed = args.start_seed + k
        run_dir = out_root / f"seed-{seed}"
        print(f"[multi-seed] seed={seed} → {run_dir}", flush=True)
        rows.append(_run_one(config_path, run_dir, seed, args.smoke, extra))

    best_metrics = [r["best_metric"] for r in rows if r.get("best_metric") is not None]
    summary: dict[str, Any] = {
        "iter": iter_dir.name,
        "config": str(config_path),
        "smoke": args.smoke,
        "seeds": [r["seed"] for r in rows],
        "n_ok": sum(1 for r in rows if r["ok"]),
        "n_total": len(rows),
        "rows": rows,
        "best_metric_mean": statistics.fmean(best_metrics) if best_metrics else None,
        "best_metric_stdev": (
            statistics.pstdev(best_metrics) if len(best_metrics) > 1 else 0.0
        ),
        "best_metric_min": min(best_metrics) if best_metrics else None,
        "best_metric_max": max(best_metrics) if best_metrics else None,
        "wall_time": time.time(),
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
