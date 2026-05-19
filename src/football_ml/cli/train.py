"""Batch training CLI for football-ml.

Wraps the same Trainer the FastAPI server uses, but writes structured
artifacts to a run directory instead of streaming to a WebSocket. Designed
to be invoked once per iteration by a search loop (`/goal` skill).

Outputs (all under --run-dir):
    config.yaml      verbatim copy of the input config
    run_meta.json    git SHA, library versions, dataset snapshot, CLI args
    metrics.jsonl    one JSON line per epoch (train/val metrics)
    status.json      current phase + epoch + finished flag + exit reason
    log.txt          captured trainer logs
    gpu.jsonl        nvidia-smi samples (if --gpu-monitor)
    checkpoint.pt    best-model snapshot (only if training improved)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
from dataclasses import fields
from pathlib import Path
from typing import Any

import yaml

from football_ml.training.config import EpochResult, TrainingConfig
from football_ml.utils.gpu_monitor import GpuMonitor
from football_ml.utils.preflight import preflight
from football_ml.utils.run_meta import append_run_meta, write_run_meta


_VALID_HEADS = {"match_outcome", "scoreline", "player_stat", "match_stat"}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="football-ml-train",
        description="Run one training iteration; write structured artifacts.",
    )
    p.add_argument("--config", required=True, help="Path to pipeline YAML.")
    p.add_argument("--run-dir", required=True, help="Output directory for this run.")
    p.add_argument("--smoke", action="store_true", help="Smoke mode: short, sampled.")
    p.add_argument("--max-samples", type=int, default=None)
    p.add_argument("--max-epochs", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--validate-only", action="store_true", help="Build model, then exit.")
    p.add_argument("--gpu-monitor", action="store_true")
    p.add_argument("--gpu-monitor-interval", type=float, default=5.0)
    p.add_argument("--force", action="store_true", help="Bypass GPU preflight.")
    p.add_argument(
        "--split-strategy",
        default=None,
        help="Override training_config.split_strategy.",
    )
    p.add_argument(
        "--split-params",
        default=None,
        help="JSON dict for training_config.split_params.",
    )
    return p.parse_args(argv)


def _filter_training_config_kwargs(d: dict[str, Any]) -> dict[str, Any]:
    """Keep only keys that TrainingConfig actually accepts."""
    known = {f.name for f in fields(TrainingConfig)}
    return {k: v for k, v in d.items() if k in known}


def _node_params(pipeline_data: dict, node_type: str) -> dict[str, Any]:
    """Return params of the first node of the given type, or empty dict."""
    for node in pipeline_data.get("nodes", {}).values():
        if node.get("type") == node_type:
            return node.get("params", {}) or {}
    return {}


def _head_type(pipeline_data: dict) -> str:
    for node in pipeline_data.get("nodes", {}).values():
        t = node.get("type")
        if t in _VALID_HEADS:
            return t
    return "match_outcome"


def _write_status(run_dir: Path, status: dict[str, Any]) -> None:
    (run_dir / "status.json").write_text(json.dumps(status, indent=2))


def _append_metric(run_dir: Path, result: EpochResult) -> None:
    line = json.dumps(result.to_dict(), default=str)
    with (run_dir / "metrics.jsonl").open("a", buffering=1) as f:
        f.write(line + "\n")


def _build_training_config(
    raw_training: dict[str, Any], args: argparse.Namespace
) -> TrainingConfig:
    kwargs = _filter_training_config_kwargs(dict(raw_training))
    if args.seed is not None:
        kwargs["seed"] = args.seed
    if args.max_samples is not None:
        kwargs["max_samples"] = args.max_samples
    if args.max_epochs is not None:
        kwargs["max_epochs"] = args.max_epochs
    if args.split_strategy is not None:
        kwargs["split_strategy"] = args.split_strategy
    if args.split_params is not None:
        kwargs["split_params"] = json.loads(args.split_params)
    if args.gpu_monitor:
        kwargs["gpu_monitor"] = True
        kwargs["gpu_monitor_interval"] = args.gpu_monitor_interval

    if args.smoke:
        # Smoke defaults; user-provided overrides win.
        kwargs.setdefault("max_samples", 1000)
        kwargs.setdefault("max_epochs", 5)
        kwargs.setdefault("seed", 0)

    config = TrainingConfig(**kwargs)
    if config.max_epochs is not None:
        config.epochs = min(config.epochs, config.max_epochs)
    return config


def _build_model_and_data(
    pipeline_data: dict, config: TrainingConfig, db_path: str, source_config: dict,
    log,
):
    """Return (model, train_batches, val_batches, test_batches).

    Honors hetero_gnn / gru_temporal / head node params from the YAML so search
    can actually influence the model. Falls back to FlatPipeline when no
    hetero_gnn node is present.
    """
    from football_ml.config import PipelineConfig
    from football_ml.server.data_loader import (
        _has_hetero_gnn,
        load_flat_data,
        load_hetero_data,
    )

    use_hetero = _has_hetero_gnn(pipeline_data)
    head = _head_type(pipeline_data)
    config.heads = [head]

    if use_hetero:
        train, val, test, metadata, num_teams, num_comps, feature_dims = load_hetero_data(
            db_path, source_config, config, log=log
        )
        from football_ml.pipeline_hetero import HeteroPipeline

        pipeline_cfg = PipelineConfig()
        gnn_cfg = pipeline_cfg.composition.hetero_gnn
        hg = _node_params(pipeline_data, "hetero_gnn")
        gnn_cfg.d_model = int(hg.get("d_model", 64))
        gnn_cfg.num_heads = int(hg.get("num_heads", 4))
        gnn_cfg.num_layers = int(hg.get("num_layers", 2))
        gnn_cfg.dropout = float(hg.get("dropout", 0.2))
        gnn_cfg.readout_dim = 2 * gnn_cfg.d_model

        gru = _node_params(pipeline_data, "gru_temporal")
        pipeline_cfg.temporal.input_dim = int(gru.get("input_dim", gnn_cfg.readout_dim))
        pipeline_cfg.temporal.hidden_dim = int(gru.get("hidden_dim", 64))
        pipeline_cfg.temporal.output_dim = int(gru.get("output_dim", 64))

        head_params = _node_params(pipeline_data, head)
        head_dim = int(head_params.get("input_dim", pipeline_cfg.temporal.output_dim))
        for h in ("match_outcome", "scoreline", "match_stat"):
            if hasattr(pipeline_cfg.heads, h):
                getattr(pipeline_cfg.heads, h).input_dim = head_dim

        model = HeteroPipeline(
            pipeline_cfg, metadata, num_teams, num_comps,
            head=head, feature_dims=feature_dims,
        )
        log("info", (
            f"HeteroGNN d_model={gnn_cfg.d_model} heads={gnn_cfg.num_heads} "
            f"layers={gnn_cfg.num_layers} dropout={gnn_cfg.dropout}"
        ))
        return model, train, val, test

    train, val, test, feat_dim = load_flat_data(
        db_path, source_config, config, log=log
    )
    from football_ml.pipeline_flat import FlatPipeline

    flat = _node_params(pipeline_data, "csv_source")  # placeholder; rarely set
    model = FlatPipeline(
        input_dim=feat_dim,
        hidden_dim=int(flat.get("hidden_dim", 64)),
        num_layers=int(flat.get("num_layers", 3)),
        dropout=float(flat.get("dropout", 0.3)),
        num_classes=3,
    )
    log("info", f"FlatPipeline: {feat_dim} → 64 → 64 → 3")
    return model, train, val, test


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = Path(args.config).expanduser().resolve()
    if not cfg_path.exists():
        sys.stderr.write(f"Config not found: {cfg_path}\n")
        return 2

    pipeline_data = yaml.safe_load(cfg_path.read_text()) or {}
    # Always preserve a verbatim copy of the input config inside the run dir.
    shutil.copy2(cfg_path, run_dir / "config.yaml")

    raw_training = pipeline_data.get("training", {}) if isinstance(pipeline_data, dict) else {}
    config = _build_training_config(raw_training, args)

    # Find data source.
    from football_ml.server.data_loader import _parse_pipeline_yaml

    db_path, source_config = _parse_pipeline_yaml(pipeline_data)
    if db_path is None:
        sys.stderr.write("No sqlite_source node found in pipeline YAML.\n")
        return 2

    # Write initial run_meta and status BEFORE preflight so a refused launch leaves a trace.
    write_run_meta(
        run_dir,
        cli_args=sys.argv,
        config={"training": config.to_dict(), "pipeline_path": str(cfg_path)},
        db_path=db_path,
    )
    _write_status(run_dir, {
        "phase": "starting",
        "current_epoch": 0,
        "finished": False,
        "exit_code": None,
        "reason": "",
        "start_time": time.time(),
    })

    verdict = preflight(force=args.force)
    if not verdict.ok:
        _write_status(run_dir, {
            "phase": "refused",
            "current_epoch": 0,
            "finished": True,
            "exit_code": 3,
            "reason": verdict.reason,
            "preflight_sample": verdict.sample,
        })
        append_run_meta(run_dir, {"end_time": time.time(), "exit_code": 3})
        sys.stderr.write(verdict.reason + "\n")
        return 3

    # Logging: tee to log.txt and stdout.
    log_path = run_dir / "log.txt"
    log_file = log_path.open("a", buffering=1)

    def log(level: str, message: str) -> None:
        line = f"[{level}] {message}"
        print(line, flush=True)
        log_file.write(line + "\n")

    log("info", f"Preflight: {verdict.reason}")
    if verdict.sample:
        log("info", f"GPU sample: {verdict.sample}")

    monitor: GpuMonitor | None = None
    if config.gpu_monitor:
        monitor = GpuMonitor(run_dir / "gpu.jsonl", interval=config.gpu_monitor_interval)
        monitor.start()
        log("info", f"GPU monitor running every {config.gpu_monitor_interval}s")

    exit_code = 0
    try:
        model, train_data, val_data, _test_data = _build_model_and_data(
            pipeline_data, config, db_path, source_config or {}, log
        )
        if args.validate_only:
            log("info", "validate-only: model + data built; skipping training.")
            _write_status(run_dir, {
                "phase": "validated",
                "current_epoch": 0,
                "finished": True,
                "exit_code": 0,
                "reason": "validate-only",
            })
            return 0

        # Trainer writes checkpoints to <checkpoint_dir>/checkpoint.pt
        config.checkpoint_dir = str(run_dir)

        from football_ml.training.trainer import Trainer
        trainer = Trainer(model, config)

        def on_epoch(result: EpochResult) -> None:
            _append_metric(run_dir, result)
            _write_status(run_dir, {
                "phase": "training",
                "current_epoch": result.epoch,
                "finished": False,
                "exit_code": None,
                "reason": "",
                "best_metric": result.best_metric,
                "is_best": result.is_best,
                "train_loss": result.train_loss,
                "val_loss": result.val_loss,
                "metrics": result.metrics,
            })

        _write_status(run_dir, {
            "phase": "training",
            "current_epoch": 0,
            "finished": False,
            "exit_code": None,
            "reason": "",
        })
        results = trainer.train(
            train_data, val_data, callback=on_epoch, log_callback=log
        )
        best = max((r.best_metric for r in results), default=0.0)
        _write_status(run_dir, {
            "phase": "completed",
            "current_epoch": results[-1].epoch if results else 0,
            "finished": True,
            "exit_code": 0,
            "reason": "training complete",
            "best_metric": best,
            "epochs_run": len(results),
        })
        log("info", f"Best metric: {best:.4f}")
    except Exception as exc:
        exit_code = 1
        log("error", f"{type(exc).__name__}: {exc}")
        log_file.write(traceback.format_exc() + "\n")
        _write_status(run_dir, {
            "phase": "failed",
            "current_epoch": 0,
            "finished": True,
            "exit_code": 1,
            "reason": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        })
    finally:
        if monitor is not None:
            monitor.stop()
        append_run_meta(run_dir, {"end_time": time.time(), "exit_code": exit_code})
        log_file.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
