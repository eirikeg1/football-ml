"""Build / read a per-search leaderboard.

Scans `<results-dir>/runs/iter-*/` and emits one summary row per finished run.
Output format:
    --format jsonl   one JSON line per row, sorted by descending best_metric
    --format md      Markdown table (default)
    --format csv     plain CSV

Designed to be invoked by the goal-search skill between iterations to take
stock of what's been tried.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

from football_ml.search._common import (
    diff_configs,
    iter_run_dirs,
    load_baseline,
    load_config,
    load_metrics,
    load_status,
    primary_metric_from_status,
    summarize_delta,
)


def collect_rows(results_dir: Path) -> list[dict[str, Any]]:
    baseline = load_baseline(results_dir)
    rows: list[dict[str, Any]] = []
    for run in iter_run_dirs(results_dir):
        status = load_status(run)
        metrics = load_metrics(run)
        config = load_config(run)
        delta = diff_configs(baseline, config) if baseline else {}
        last_metric_row = metrics[-1] if metrics else {}
        row = {
            "iter": run.name,
            "phase": status.get("phase", "unknown"),
            "finished": bool(status.get("finished", False)),
            "exit_code": status.get("exit_code"),
            "reason": status.get("reason", ""),
            "epochs_run": len(metrics),
            "best_metric": primary_metric_from_status(status),
            "final_train_loss": last_metric_row.get("train_loss"),
            "final_val_loss": last_metric_row.get("val_loss"),
            "final_metrics": last_metric_row.get("metrics", {}),
            "delta": summarize_delta(delta),
        }
        rows.append(row)
    # Sort by best_metric desc, None last.
    rows.sort(key=lambda r: (r["best_metric"] is None, -(r["best_metric"] or 0.0)))
    return rows


def to_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_(no completed runs)_\n"
    header = (
        "| iter | phase | best | epochs | val_loss | delta |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
    )
    lines = [header.rstrip("\n")]
    for r in rows:
        best = "—" if r["best_metric"] is None else f"{r['best_metric']:.4f}"
        vl = "—" if r["final_val_loss"] is None else f"{r['final_val_loss']:.4f}"
        lines.append(
            f"| {r['iter']} | {r['phase']} | {best} | {r['epochs_run']} | {vl} | {r['delta']} |"
        )
    return "\n".join(lines) + "\n"


def to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    cols = ["iter", "phase", "finished", "exit_code", "best_metric",
            "epochs_run", "final_train_loss", "final_val_loss", "delta", "reason"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c) for c in cols})
    return buf.getvalue()


def to_jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(r, default=str) for r in rows) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="football-ml-leaderboard")
    p.add_argument("results_dir", help="Path to a results/<search>/ directory.")
    p.add_argument("--format", choices=["md", "jsonl", "csv"], default="md")
    p.add_argument(
        "--save",
        action="store_true",
        help="Also write leaderboard.{md,jsonl} into the results dir.",
    )
    args = p.parse_args(argv)

    results_dir = Path(args.results_dir).expanduser().resolve()
    if not results_dir.exists():
        sys.stderr.write(f"Results dir not found: {results_dir}\n")
        return 2
    rows = collect_rows(results_dir)
    if args.format == "md":
        out = to_markdown(rows)
    elif args.format == "csv":
        out = to_csv(rows)
    else:
        out = to_jsonl(rows)
    print(out, end="")
    if args.save:
        (results_dir / "leaderboard.jsonl").write_text(to_jsonl(rows))
        (results_dir / "leaderboard.md").write_text(to_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
