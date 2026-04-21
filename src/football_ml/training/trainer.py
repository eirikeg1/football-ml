"""Training loop with metric streaming, early stopping, and checkpointing."""

from __future__ import annotations

import time
import threading
from collections.abc import Callable
from pathlib import Path

import torch
from torch import Tensor, nn
from torch.optim import SGD, Adam, AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, StepLR, LinearLR

from football_ml.config import PipelineConfig
from football_ml.training.config import EpochResult, ResourceUsage, TrainingConfig
from football_ml.training.losses import get_loss
from football_ml.training.metrics import compute_metrics


def get_device() -> torch.device:
    """Return the best available device (CUDA > CPU)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _to_device(obj, device: torch.device):
    """Recursively move tensors, HeteroData, and Batch objects to device."""
    if isinstance(obj, torch.Tensor):
        return obj.to(device)
    if isinstance(obj, dict):
        return {k: _to_device(v, device) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_to_device(v, device) for v in obj)
    # PyG Data / HeteroData / Batch
    if hasattr(obj, "to"):
        return obj.to(device)
    return obj


class Trainer:
    """Manages the training loop for a football-ml pipeline.

    Automatically uses GPU if available, falling back to CPU.

    Supports:
    - Multi-head training with weighted losses
    - Early stopping on a monitored metric
    - Graceful stop/pause via threading events
    - Per-epoch callbacks for live metric streaming
    - Checkpoint saving for best model
    """

    def __init__(
        self,
        model: nn.Module,
        training_config: TrainingConfig,
    ) -> None:
        self.device = get_device()
        self.model = model.to(self.device)
        self.config = training_config

        # Optimizer
        optim_map = {"adam": Adam, "sgd": SGD, "adamw": AdamW}
        optim_cls = optim_map.get(training_config.optimizer, Adam)
        self.optimizer = optim_cls(
            model.parameters(),
            lr=training_config.learning_rate,
            weight_decay=training_config.weight_decay,
        )

        # LR Scheduler
        self.scheduler = self._build_scheduler()

        # Loss functions per head
        self.losses: dict[str, nn.Module] = {}
        for head in training_config.heads:
            override = training_config.loss_overrides.get(head)
            self.losses[head] = get_loss(head, override)

        # Loss weights
        self.loss_weights: dict[str, float] = {}
        for head in training_config.heads:
            self.loss_weights[head] = training_config.loss_weights.get(head, 1.0)

        # Control events
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially

        # Tracking
        self._best_metric = float("-inf")
        self._patience_counter = 0

    def _build_scheduler(self):
        cfg = self.config
        if cfg.scheduler == "step":
            step_size = cfg.scheduler_params.get("step_size", 10)
            gamma = cfg.scheduler_params.get("gamma", 0.1)
            return StepLR(self.optimizer, step_size=int(step_size), gamma=gamma)
        elif cfg.scheduler == "cosine":
            return CosineAnnealingLR(self.optimizer, T_max=cfg.epochs)
        elif cfg.scheduler == "warmup":
            warmup_epochs = cfg.scheduler_params.get("warmup_epochs", 5)
            return LinearLR(
                self.optimizer,
                start_factor=0.1,
                total_iters=int(warmup_epochs),
            )
        return None

    def train(
        self,
        train_data: list[dict[str, Tensor]],
        val_data: list[dict[str, Tensor]] | None = None,
        callback: Callable[[EpochResult], None] | None = None,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> list[EpochResult]:
        """Run the training loop.

        Each item in train_data/val_data is a dict with keys:
        - "inputs": dict of input tensors for the model's forward()
        - "targets": dict of head_name -> target tensor

        Args:
            train_data: list of training samples (each is a batch dict).
            val_data: optional validation samples.
            callback: called with EpochResult after each epoch.
            log_callback: called with (level, message) for log events.

        Returns:
            List of EpochResults for all completed epochs.
        """
        def log(level: str, msg: str):
            if log_callback:
                log_callback(level, msg)

        device_name = str(self.device)
        if self.device.type == "cuda":
            device_name = f"cuda ({torch.cuda.get_device_name(0)})"
        log("info", f"Device: {device_name}")
        log("info", f"Starting training: {self.config.epochs} epochs")
        log("info", f"Optimizer: {self.config.optimizer}, LR: {self.config.learning_rate}")
        log("info", f"Heads: {self.config.heads}")
        log("info", f"Training batches: {len(train_data)}, Validation batches: {len(val_data) if val_data else 0}")

        self.model.train()
        results: list[EpochResult] = []

        for epoch in range(1, self.config.epochs + 1):
            if self._stop_event.is_set():
                log("info", "Training stopped by user")
                break

            # Handle pause
            self._pause_event.wait()

            start_time = time.time()

            # Training step
            train_loss = self._run_epoch(train_data, training=True)

            # Validation step
            val_loss = 0.0
            val_metrics: dict[str, float] = {}
            if val_data:
                val_loss, val_metrics = self._validate(val_data)

            elapsed = time.time() - start_time

            # LR scheduler step
            current_lr = self.optimizer.param_groups[0]["lr"]
            if self.scheduler:
                self.scheduler.step()

            # Determine primary metric for early stopping
            primary_metric = 0.0
            if val_metrics:
                primary_metric = next(iter(val_metrics.values()), 0.0)

            is_best = primary_metric > self._best_metric
            if is_best:
                self._best_metric = primary_metric
                self._patience_counter = 0
                self._save_checkpoint(epoch)
            else:
                self._patience_counter += 1

            result = EpochResult(
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
                learning_rate=current_lr,
                metrics=val_metrics,
                best_metric=self._best_metric,
                is_best=is_best,
                elapsed_seconds=round(elapsed, 2),
                resources=ResourceUsage.snapshot(),
            )
            results.append(result)

            if callback:
                callback(result)

            log_msg = f"Epoch {epoch}/{self.config.epochs} - train_loss: {train_loss:.4f}"
            if val_data:
                log_msg += f" - val_loss: {val_loss:.4f}"
                for k, v in val_metrics.items():
                    log_msg += f" - {k}: {v:.4f}"
            log("info", log_msg)

            # Early stopping
            if (
                self.config.early_stopping_patience > 0
                and self._patience_counter >= self.config.early_stopping_patience
                and val_data
            ):
                log("warning", f"Early stopping at epoch {epoch} (patience {self.config.early_stopping_patience})")
                break

        log("info", f"Training complete. Best metric: {self._best_metric:.4f}")
        return results

    def _run_epoch(
        self, data: list[dict[str, Tensor]], training: bool = True
    ) -> float:
        """Run one epoch over the data."""
        if training:
            self.model.train()
        else:
            self.model.eval()

        total_loss = 0.0
        count = 0

        context = torch.no_grad() if not training else torch.enable_grad()
        with context:
            for batch in data:
                if self._stop_event.is_set():
                    break

                inputs = _to_device(batch["inputs"], self.device)
                targets = _to_device(batch["targets"], self.device)

                if training:
                    self.optimizer.zero_grad()

                predictions = self.model(**inputs)

                batch_loss = torch.tensor(0.0, device=self.device)
                for head_name in self.config.heads:
                    if head_name not in targets:
                        continue
                    loss_fn = self.losses[head_name]
                    head_loss = loss_fn(predictions, targets[head_name])
                    batch_loss = batch_loss + head_loss * self.loss_weights[head_name]

                if training:
                    batch_loss.backward()
                    self.optimizer.step()

                total_loss += batch_loss.item()
                count += 1

        return total_loss / max(count, 1)

    def _validate(
        self, val_data: list[dict[str, Tensor]]
    ) -> tuple[float, dict[str, float]]:
        """Run validation and compute metrics."""
        val_loss = self._run_epoch(val_data, training=False)

        # Compute metrics
        all_preds: list[Tensor] = []
        all_targets: list[Tensor] = []

        self.model.eval()
        with torch.no_grad():
            for batch in val_data:
                inputs = _to_device(batch["inputs"], self.device)
                targets = _to_device(batch["targets"], self.device)
                predictions = self.model(**inputs)
                all_preds.append(predictions)
                primary_head = self.config.heads[0]
                if primary_head in targets:
                    all_targets.append(targets[primary_head])

        metrics: dict[str, float] = {}
        if all_preds and all_targets:
            preds_cat = torch.cat(all_preds, dim=0)
            targets_cat = torch.cat(all_targets, dim=0)
            primary_head = self.config.heads[0]
            metrics = compute_metrics(
                primary_head, preds_cat, targets_cat, self.config.metrics
            )

        return val_loss, metrics

    def _save_checkpoint(self, epoch: int) -> None:
        """Save model checkpoint."""
        ckpt_dir = Path(self.config.checkpoint_dir)
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        path = ckpt_dir / "best_model.pt"
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "best_metric": self._best_metric,
            },
            path,
        )

    def stop(self) -> None:
        """Signal the training loop to stop."""
        self._stop_event.set()
        self._pause_event.set()  # unpause if paused so it can exit

    def pause(self) -> None:
        """Pause the training loop."""
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume the training loop."""
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()
