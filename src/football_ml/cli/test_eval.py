"""One-shot test-set evaluation.

Loads the trained checkpoint from a finished run directory, rebuilds the
model using the same config, runs inference on the held-out test split, and
writes `<run-dir>/test-eval-results.json`. Designed to be called at most
once per search (the goal-search skill gates this).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch
import yaml
from torch import Tensor

from football_ml.cli.train import _build_model_and_data, _build_training_config
from football_ml.training.config import TrainingConfig
from football_ml.training.metrics import compute_metrics
from football_ml.training.trainer import _to_device, get_device


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="football-ml-test-eval",
        description="Evaluate a trained checkpoint on the held-out test split.",
    )
    p.add_argument("--run-dir", required=True, help="Run directory containing config.yaml + checkpoint.pt")
    p.add_argument("--checkpoint", default=None, help="Override checkpoint path.")
    p.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <run-dir>/test-eval-results.json).",
    )
    return p.parse_args(argv)


def _evaluate(model, batches: list[dict], heads: list[str], metrics: list[str]) -> dict[str, Any]:
    device = get_device()
    model.to(device).eval()
    all_preds: list[Tensor] = []
    all_targets: list[Tensor] = []
    with torch.no_grad():
        for batch in batches:
            inputs = _to_device(batch["inputs"], device)
            targets = _to_device(batch["targets"], device)
            preds = model(**inputs)
            all_preds.append(preds)
            primary = heads[0]
            if primary in targets:
                all_targets.append(targets[primary])
    if not all_preds or not all_targets:
        return {"n_samples": 0, "metrics": {}}
    preds_cat = torch.cat(all_preds, dim=0)
    targets_cat = torch.cat(all_targets, dim=0)
    metric_values = compute_metrics(heads[0], preds_cat, targets_cat, metrics)
    return {
        "n_samples": int(targets_cat.shape[0]),
        "metrics": {k: float(v) for k, v in metric_values.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        sys.stderr.write(f"Run dir not found: {run_dir}\n")
        return 2

    cfg_path = run_dir / "config.yaml"
    if not cfg_path.exists():
        sys.stderr.write(f"Expected config at {cfg_path}\n")
        return 2

    ckpt_path = Path(args.checkpoint) if args.checkpoint else (run_dir / "checkpoint.pt")
    if not ckpt_path.exists():
        sys.stderr.write(f"Checkpoint not found: {ckpt_path}\n")
        return 2

    pipeline_data = yaml.safe_load(cfg_path.read_text()) or {}
    raw_training = pipeline_data.get("training", {}) if isinstance(pipeline_data, dict) else {}

    # Rebuild config; force max_samples=None for full test eval.
    fake_args = argparse.Namespace(
        seed=None, max_samples=None, max_epochs=None, split_strategy=None,
        split_params=None, gpu_monitor=False, gpu_monitor_interval=5.0, smoke=False,
    )
    config: TrainingConfig = _build_training_config(raw_training, fake_args)
    config.max_samples = None  # never smoke-mode the test eval

    from football_ml.server.data_loader import _parse_pipeline_yaml
    db_path, source_config = _parse_pipeline_yaml(pipeline_data)
    if db_path is None:
        sys.stderr.write("No sqlite_source node in pipeline YAML.\n")
        return 2

    def log(level: str, message: str) -> None:
        print(f"[{level}] {message}", flush=True)

    model, _train, _val, test = _build_model_and_data(
        pipeline_data, config, db_path, source_config or {}, log
    )
    ckpt = torch.load(ckpt_path, map_location=get_device(), weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])

    log("info", f"Evaluating on {len(test)} test batches…")
    summary = _evaluate(model, test, config.heads, config.metrics)
    summary.update(
        {
            "run_dir": str(run_dir),
            "checkpoint": str(ckpt_path),
            "checkpoint_epoch": ckpt.get("epoch"),
            "split_strategy": config.split_strategy,
            "split_params": config.split_params,
            "heads": config.heads,
            "metrics_requested": config.metrics,
            "eval_time": time.time(),
        }
    )

    out_path = Path(args.output) if args.output else (run_dir / "test-eval-results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    log("info", f"Wrote {out_path}")
    print(json.dumps(summary["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
