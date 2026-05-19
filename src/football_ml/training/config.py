"""Training configuration dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class TrainingConfig:
    """Configuration for a training run."""

    optimizer: str = "adam"  # "adam" | "sgd" | "adamw"
    learning_rate: float = 1e-3
    weight_decay: float = 0.0
    epochs: int = 50
    batch_size: int = 32
    val_split: float = 0.2  # legacy; only consulted by split_strategy=time_percentile fallbacks
    early_stopping_patience: int = 10
    heads: list[str] = field(default_factory=lambda: ["match_outcome"])
    loss_overrides: dict[str, str] = field(default_factory=dict)
    loss_weights: dict[str, float] = field(default_factory=dict)
    metrics: list[str] = field(default_factory=lambda: ["accuracy"])
    scheduler: str | None = None  # "step" | "cosine" | "warmup"
    scheduler_params: dict = field(default_factory=dict)
    checkpoint_dir: str = "checkpoints"

    # Reproducibility + smoke-mode controls used by the CLI / search loop.
    seed: int | None = None
    max_samples: int | None = None  # uniformly stride-downsample before split when set
    max_epochs: int | None = None  # caps `epochs` at runtime; lets smoke override full configs

    # Parametric three-way split. Mechanism lives in football_ml.data.splits.
    split_strategy: str = "latest_season_per_competition"
    split_params: dict = field(default_factory=dict)

    # nvidia-smi sampler controls (off by default; CLI flips these on).
    gpu_monitor: bool = False
    gpu_monitor_interval: float = 5.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResourceUsage:
    """System resource usage snapshot."""

    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    ram_percent: float = 0.0
    gpu_vram_used_gb: float = 0.0
    gpu_vram_total_gb: float = 0.0
    gpu_vram_percent: float = 0.0
    gpu_name: str = ""
    cpu_percent: float = 0.0

    @staticmethod
    def snapshot() -> "ResourceUsage":
        """Capture current resource usage."""
        import psutil

        mem = psutil.virtual_memory()
        usage = ResourceUsage(
            ram_used_gb=round(mem.used / 1e9, 2),
            ram_total_gb=round(mem.total / 1e9, 2),
            ram_percent=round(mem.percent, 1),
            cpu_percent=round(psutil.cpu_percent(interval=None), 1),
        )

        # GPU VRAM (if available)
        try:
            import torch
            if torch.cuda.is_available():
                usage.gpu_name = torch.cuda.get_device_name(0)
                usage.gpu_vram_used_gb = round(torch.cuda.memory_reserved(0) / 1e9, 2)
                usage.gpu_vram_total_gb = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
                if usage.gpu_vram_total_gb > 0:
                    usage.gpu_vram_percent = round(usage.gpu_vram_used_gb / usage.gpu_vram_total_gb * 100, 1)
        except Exception:
            pass

        return usage


@dataclass
class EpochResult:
    """Result of a single training epoch, streamed to the UI."""

    epoch: int
    train_loss: float
    val_loss: float
    learning_rate: float
    metrics: dict[str, float]
    best_metric: float
    is_best: bool
    elapsed_seconds: float
    resources: ResourceUsage | None = None

    def to_dict(self) -> dict:
        d = {"type": "epoch", **asdict(self)}
        if self.resources:
            d["resources"] = asdict(self.resources)
        else:
            d.pop("resources", None)
        return d
