"""Loss function registry for prediction heads."""

from __future__ import annotations

import torch
from torch import Tensor, nn


class ScorelineLoss(nn.Module):
    """Cross-entropy loss applied independently to home and away goal distributions."""

    def __init__(self) -> None:
        super().__init__()
        self.ce = nn.CrossEntropyLoss()

    def forward(self, predictions: Tensor, targets: Tensor) -> Tensor:
        """Compute loss for scoreline predictions.

        Args:
            predictions: (batch, 2, max_goals+1) logits.
            targets: (batch, 2) integer goal counts for [home, away].
        """
        home_loss = self.ce(predictions[:, 0, :], targets[:, 0].long())
        away_loss = self.ce(predictions[:, 1, :], targets[:, 1].long())
        return (home_loss + away_loss) / 2


class FocalLoss(nn.Module):
    """Focal loss for class-imbalanced classification."""

    def __init__(self, gamma: float = 2.0) -> None:
        super().__init__()
        self.gamma = gamma

    def forward(self, predictions: Tensor, targets: Tensor) -> Tensor:
        ce_loss = nn.functional.cross_entropy(predictions, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()


# Registry: head_type -> {loss_name: loss_factory}
LOSS_REGISTRY: dict[str, dict[str, type[nn.Module] | callable]] = {
    "match_outcome": {
        "cross_entropy": nn.CrossEntropyLoss,
        "focal": FocalLoss,
    },
    "scoreline": {
        "cross_entropy": ScorelineLoss,
        "poisson": lambda: nn.PoissonNLLLoss(log_input=False),
    },
    "player_stat": {
        "mse": nn.MSELoss,
        "huber": nn.HuberLoss,
        "l1": nn.L1Loss,
    },
    "match_stat": {
        "mse": nn.MSELoss,
        "huber": nn.HuberLoss,
        "l1": nn.L1Loss,
    },
}

DEFAULT_LOSSES: dict[str, str] = {
    "match_outcome": "cross_entropy",
    "scoreline": "cross_entropy",
    "player_stat": "mse",
    "match_stat": "mse",
}


def get_loss(head_type: str, loss_name: str | None = None) -> nn.Module:
    """Instantiate a loss function for a given head type.

    Args:
        head_type: prediction head type (e.g., "match_outcome").
        loss_name: specific loss name. If None, uses the default.

    Returns:
        Instantiated loss module.
    """
    if head_type not in LOSS_REGISTRY:
        raise ValueError(f"Unknown head type: {head_type}")

    name = loss_name or DEFAULT_LOSSES[head_type]
    registry = LOSS_REGISTRY[head_type]
    if name not in registry:
        raise ValueError(
            f"Unknown loss '{name}' for head '{head_type}'. "
            f"Available: {list(registry.keys())}"
        )

    factory = registry[name]
    return factory()


def get_available_losses() -> dict[str, dict[str, str]]:
    """Return available losses per head type with defaults marked.

    Returns:
        Dict of head_type -> {"default": loss_name, "options": [loss_names]}
    """
    result = {}
    for head_type, losses in LOSS_REGISTRY.items():
        result[head_type] = {
            "default": DEFAULT_LOSSES[head_type],
            "options": list(losses.keys()),
        }
    return result
