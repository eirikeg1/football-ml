"""FastAPI application with REST endpoints and WebSocket for training."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from football_ml.training.config import EpochResult, TrainingConfig
from football_ml.training.losses import get_available_losses
from football_ml.training.metrics import get_available_metrics

app = FastAPI(title="football-ml Training Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket connection manager ────────────────────────────────────


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Training session state ──────────────────────────────────────────


@dataclass
class TrainingSession:
    """Holds the state of the current training run."""

    run_id: str = ""
    status: str = "idle"  # idle | training | paused | completed | error
    epoch: int = 0
    total_epochs: int = 0
    trainer: object | None = None  # Trainer instance
    thread: threading.Thread | None = None
    error_message: str = ""


session = TrainingSession()

# Async event loop reference for broadcasting from training thread
_loop: asyncio.AbstractEventLoop | None = None


def _broadcast_sync(message: dict) -> None:
    """Broadcast a message from the training thread (sync context)."""
    if _loop is not None:
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), _loop)


# ── Request/response models ────────────────────────────────────────


class TrainRequest(BaseModel):
    pipeline_yaml: str
    training_config: dict


class StatusResponse(BaseModel):
    status: str
    run_id: str = ""
    epoch: int = 0
    total_epochs: int = 0
    error_message: str = ""


# ── REST endpoints ──────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    global _loop
    _loop = asyncio.get_event_loop()


@app.post("/api/train")
async def start_training(request: TrainRequest) -> dict:
    """Start a new training run."""
    if session.status == "training":
        return {"status": "error", "message": "Training already in progress"}

    run_id = str(uuid.uuid4())[:8]
    session.run_id = run_id
    session.status = "training"
    session.epoch = 0
    session.error_message = ""

    config = TrainingConfig(**request.training_config)
    session.total_epochs = config.epochs

    def run_training():
        try:
            _broadcast_sync({"type": "status", "status": "training", "message": "Training started"})
            _broadcast_sync({"type": "log", "level": "info", "message": "Initializing pipeline..."})

            from football_ml.training.trainer import Trainer
            from football_ml.config import PipelineConfig
            from football_ml.server.data_loader import (
                _parse_pipeline_yaml,
                _has_hetero_gnn,
                load_hetero_data,
                load_flat_data,
            )

            import yaml as pyyaml
            pipeline_data = pyyaml.safe_load(request.pipeline_yaml) or {}

            def on_log(level: str, message: str):
                _broadcast_sync({"type": "log", "level": level, "message": message})

            # Extract data source config from the pipeline YAML
            db_path, source_config = _parse_pipeline_yaml(pipeline_data)
            use_hetero = _has_hetero_gnn(pipeline_data)

            if db_path and use_hetero:
                # HeteroGNN path — load via SnapshotBuilder
                on_log("info", f"Loading HeteroGNN data from {db_path}")
                train_data, val_data, _test_data, metadata, num_teams, num_comps, feature_dims = load_hetero_data(
                    db_path, source_config or {}, config, log=on_log,
                )

                from football_ml.pipeline_hetero import HeteroPipeline
                pipeline_config = PipelineConfig()
                # Use smaller dims for efficiency
                gnn_cfg = pipeline_config.composition.hetero_gnn
                gnn_cfg.d_model = 64
                gnn_cfg.num_heads = 4
                gnn_cfg.num_layers = 2
                gnn_cfg.readout_dim = 128  # 2 * d_model
                pipeline_config.temporal.input_dim = gnn_cfg.readout_dim
                pipeline_config.temporal.hidden_dim = 64
                pipeline_config.temporal.output_dim = 64
                pipeline_config.heads.match_outcome.input_dim = 64
                pipeline_config.heads.scoreline.input_dim = 64
                pipeline_config.heads.match_stat.input_dim = 64

                model = HeteroPipeline(
                    pipeline_config, metadata, num_teams, num_comps,
                    head=config.heads[0],
                    feature_dims=feature_dims,
                )
                on_log("info", f"HeteroGNN: d_model={gnn_cfg.d_model}, heads={gnn_cfg.num_heads}, layers={gnn_cfg.num_layers}")

            elif db_path:
                # Flat pipeline — rolling historical features → simple MLP
                on_log("info", f"Loading flat data from {db_path}")
                train_data, val_data, _test_data, feat_dim = load_flat_data(
                    db_path, source_config or {}, config, log=on_log,
                )

                from football_ml.pipeline_flat import FlatPipeline
                model = FlatPipeline(
                    input_dim=feat_dim,
                    hidden_dim=64,
                    num_layers=3,
                    dropout=0.3,
                    num_classes=3,
                )
                on_log("info", f"FlatPipeline: {feat_dim} → 64 → 64 → 3")

            else:
                raise ValueError(
                    "No SQLite data source found in pipeline. "
                    "Add a SQLite Database node in the Design view."
                )

            on_log("info", f"Model: {type(model).__name__}, Head: {config.heads[0]}")

            # Create trainer
            trainer = Trainer(model, config)
            session.trainer = trainer

            def on_epoch(result: EpochResult):
                session.epoch = result.epoch
                _broadcast_sync(result.to_dict())

            def on_log(level: str, message: str):
                _broadcast_sync({"type": "log", "level": level, "message": message})

            results = trainer.train(
                train_data, val_data,
                callback=on_epoch,
                log_callback=on_log,
            )

            session.status = "completed"
            best = max((r.best_metric for r in results), default=0)
            _broadcast_sync({
                "type": "status",
                "status": "completed",
                "message": f"Training complete. Best metric: {best:.4f}",
            })

        except Exception as e:
            session.status = "error"
            session.error_message = str(e)
            _broadcast_sync({
                "type": "status",
                "status": "error",
                "message": str(e),
            })

    thread = threading.Thread(target=run_training, daemon=True)
    session.thread = thread
    thread.start()

    return {"status": "started", "run_id": run_id}


@app.post("/api/train/stop")
async def stop_training() -> dict:
    """Stop the current training run."""
    if session.trainer and session.status in ("training", "paused"):
        session.trainer.stop()
        session.status = "completed"
        await manager.broadcast({
            "type": "status",
            "status": "completed",
            "message": "Training stopped by user",
        })
        return {"status": "stopped"}
    return {"status": "not_training"}


@app.post("/api/train/pause")
async def pause_training() -> dict:
    """Toggle pause/resume for the current training run."""
    if not session.trainer or session.status not in ("training", "paused"):
        return {"status": "not_training"}

    if session.trainer.is_paused:
        session.trainer.resume()
        session.status = "training"
        await manager.broadcast({
            "type": "status",
            "status": "training",
            "message": "Training resumed",
        })
        return {"status": "resumed"}
    else:
        session.trainer.pause()
        session.status = "paused"
        await manager.broadcast({
            "type": "status",
            "status": "paused",
            "message": f"Training paused at epoch {session.epoch}",
        })
        return {"status": "paused"}


@app.get("/api/status")
async def get_status() -> StatusResponse:
    """Get the current training status."""
    return StatusResponse(
        status=session.status,
        run_id=session.run_id,
        epoch=session.epoch,
        total_epochs=session.total_epochs,
        error_message=session.error_message,
    )


@app.get("/api/heads/losses")
async def get_losses() -> dict:
    """Return available loss functions per head type."""
    return get_available_losses()


@app.get("/api/heads/metrics")
async def get_metrics() -> dict:
    """Return available metrics per head type."""
    return get_available_metrics()


# ── WebSocket endpoint ──────────────────────────────────────────────


@app.websocket("/ws/training")
async def websocket_training(ws: WebSocket):
    """WebSocket endpoint for streaming training metrics."""
    await manager.connect(ws)
    try:
        # Send current status on connect
        await ws.send_json({
            "type": "status",
            "status": session.status,
            "message": f"Connected. Status: {session.status}",
        })
        # Keep connection alive — client doesn't send messages
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
