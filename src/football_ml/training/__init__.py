"""Training infrastructure: losses, metrics, and trainer loop."""

from football_ml.training.config import EpochResult, TrainingConfig
from football_ml.training.losses import get_available_losses, get_loss
from football_ml.training.metrics import compute_metrics, get_available_metrics
from football_ml.training.trainer import Trainer

__all__ = [
    "EpochResult",
    "Trainer",
    "TrainingConfig",
    "compute_metrics",
    "get_available_losses",
    "get_available_metrics",
    "get_loss",
]
