"""Generate `SEARCH_REPORT.md` + PNG figures from a finished search dir.

The skill calls this at the end of a search. The report is opinionated about
the *general* graphs (metric-vs-iteration, top-K loss curves, hyperparameter
sensitivity, GPU timelines). For task-specific graphs (confusion matrix,
calibration, residuals) the skill is expected to wire those up separately or
append to the report.

Matplotlib is an optional dependency under [search]; if it's missing, we
write the markdown and skip the figures.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

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
from football_ml.search.leaderboard import collect_rows, to_markdown


def _try_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _figure_metric_vs_iteration(plt, results_dir: Path, fig_dir: Path) -> Path | None:
    rows = collect_rows(results_dir)
    xs = list(range(len(rows)))
    ys = [r["best_metric"] or 0.0 for r in rows]
    labels = [r["iter"] for r in rows]
    if not xs:
        return None
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, ys, marker="o")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("best val metric")
    ax.set_title("Best val metric per iteration")
    ax.grid(True, alpha=0.3)
    out = fig_dir / "metric_vs_iteration.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _figure_top_k_loss_curves(plt, results_dir: Path, fig_dir: Path, k: int = 5) -> Path | None:
    rows = collect_rows(results_dir)
    top = [r for r in rows if r["best_metric"] is not None][:k]
    if not top:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    for r in top:
        metrics = load_metrics(results_dir / "runs" / r["iter"])
        xs = [m["epoch"] for m in metrics]
        ys = [m.get("val_loss") for m in metrics]
        ax.plot(xs, ys, label=f"{r['iter']} (best={r['best_metric']:.3f})")
    ax.set_xlabel("epoch")
    ax.set_ylabel("val_loss")
    ax.set_title(f"Top-{len(top)} val loss curves")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    out = fig_dir / "top_k_loss_curves.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _figure_hyperparam_sensitivity(plt, results_dir: Path, fig_dir: Path) -> list[Path]:
    baseline = load_baseline(results_dir)
    if not baseline:
        return []
    # Collect knob → list of (value, best_metric)
    knob_to_points: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for run in iter_run_dirs(results_dir):
        status = load_status(run)
        best = primary_metric_from_status(status)
        if best is None:
            continue
        cfg = load_config(run)
        for k, (_b, c) in diff_configs(baseline, cfg).items():
            if "position" in k or "config" in k:
                continue
            knob_to_points[k].append((c, best))

    outs: list[Path] = []
    for knob, points in knob_to_points.items():
        if len(points) < 2:
            continue
        # Group by value (cast to str for binning).
        by_val: dict[str, list[float]] = defaultdict(list)
        for v, m in points:
            by_val[str(v)].append(m)
        labels = sorted(by_val, key=lambda s: (len(by_val[s]) == 1, s))
        data = [by_val[lab] for lab in labels]
        fig, ax = plt.subplots(figsize=(max(4, len(labels) * 0.8), 4))
        ax.boxplot(data, labels=labels, showmeans=True)
        ax.set_title(f"Sensitivity: {knob}")
        ax.set_ylabel("best val metric")
        ax.grid(True, alpha=0.3)
        safe = knob.replace(".", "_").replace("/", "_")
        out = fig_dir / f"sensitivity_{safe}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        plt.close(fig)
        outs.append(out)
    return outs


def _figure_gpu_timeline(plt, results_dir: Path, fig_dir: Path, k: int = 3) -> Path | None:
    rows = collect_rows(results_dir)
    top = [r for r in rows if r["best_metric"] is not None][:k]
    series: list[tuple[str, list[float], list[int]]] = []
    for r in top:
        gp = results_dir / "runs" / r["iter"] / "gpu.jsonl"
        if not gp.exists():
            continue
        ts: list[float] = []
        util: list[int] = []
        t0: float | None = None
        for line in gp.read_text().splitlines():
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            if t0 is None:
                t0 = s["ts"]
            ts.append(s["ts"] - t0)
            util.append(int(s["util_pct"]))
        if ts:
            series.append((r["iter"], ts, util))
    if not series:
        return None
    fig, ax = plt.subplots(figsize=(10, 4))
    for name, ts, util in series:
        ax.plot(ts, util, label=name, alpha=0.8)
    ax.set_xlabel("seconds since run start")
    ax.set_ylabel("GPU util %")
    ax.set_ylim(0, 100)
    ax.set_title(f"GPU utilization (top {len(series)} runs)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    out = fig_dir / "gpu_timeline.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _write_report(
    results_dir: Path, figures: list[Path], leaderboard_md: str
) -> Path:
    parts: list[str] = []
    parts.append(f"# Search report — {results_dir.name}\n")
    goal_path = results_dir / "GOAL.md"
    if goal_path.exists():
        parts.append("## Goal\n")
        parts.append(goal_path.read_text())
        parts.append("")
    hyp_path = results_dir / "HYPOTHESIS.md"
    if hyp_path.exists():
        parts.append("## Final hypothesis\n")
        parts.append(hyp_path.read_text())
        parts.append("")
    parts.append("## Leaderboard\n")
    parts.append(leaderboard_md)
    parts.append("")
    if figures:
        parts.append("## Figures\n")
        for f in figures:
            rel = f.relative_to(results_dir)
            parts.append(f"### {f.stem.replace('_', ' ').title()}\n")
            parts.append(f"![{f.stem}]({rel.as_posix()})\n")
    dead = results_dir / "DEAD_ENDS.md"
    if dead.exists() and dead.read_text().strip():
        parts.append("## Dead ends\n")
        parts.append(dead.read_text())
        parts.append("")
    test_eval = results_dir / "test-eval"
    if test_eval.exists():
        parts.append("## Test-set evaluation\n")
        for f in sorted(test_eval.glob("**/test-eval-results.json")):
            try:
                obj = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            parts.append(f"### `{f.relative_to(results_dir)}`\n")
            parts.append("```json")
            parts.append(json.dumps(obj.get("metrics", {}), indent=2))
            parts.append("```\n")
    out = results_dir / "SEARCH_REPORT.md"
    out.write_text("\n".join(parts))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="football-ml-report")
    p.add_argument("results_dir", help="Path to results/<search>/")
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args(argv)

    results_dir = Path(args.results_dir).expanduser().resolve()
    if not results_dir.exists():
        sys.stderr.write(f"Results dir not found: {results_dir}\n")
        return 2
    fig_dir = results_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    figures: list[Path] = []
    plt = _try_matplotlib()
    if plt is None:
        print("matplotlib not installed; writing report without figures.", file=sys.stderr)
    else:
        for fn in (
            _figure_metric_vs_iteration,
            _figure_top_k_loss_curves,
            _figure_gpu_timeline,
        ):
            out = fn(plt, results_dir, fig_dir)
            if out is not None:
                figures.append(out)
        figures.extend(_figure_hyperparam_sensitivity(plt, results_dir, fig_dir))

    rows = collect_rows(results_dir)
    leaderboard_md = to_markdown(rows)
    report_path = _write_report(results_dir, figures, leaderboard_md)
    print(f"Wrote {report_path}")
    if figures:
        print(f"  {len(figures)} figures under {fig_dir.relative_to(results_dir.parent)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
