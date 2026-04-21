"""Metric computation registry for prediction heads."""

from __future__ import annotations

import torch
from torch import Tensor


def _accuracy(preds: Tensor, targets: Tensor) -> float:
    predicted = preds.argmax(dim=-1)
    return (predicted == targets).float().mean().item()


def _f1_macro(preds: Tensor, targets: Tensor) -> float:
    predicted = preds.argmax(dim=-1)
    classes = torch.unique(targets)
    f1s = []
    for c in classes:
        tp = ((predicted == c) & (targets == c)).sum().float()
        fp = ((predicted == c) & (targets != c)).sum().float()
        fn = ((predicted != c) & (targets == c)).sum().float()
        precision = tp / (tp + fp + 1e-8)
        recall = tp / (tp + fn + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        f1s.append(f1.item())
    return sum(f1s) / max(len(f1s), 1)


def _f1_weighted(preds: Tensor, targets: Tensor) -> float:
    predicted = preds.argmax(dim=-1)
    classes = torch.unique(targets)
    total = len(targets)
    weighted_f1 = 0.0
    for c in classes:
        support = (targets == c).sum().float()
        tp = ((predicted == c) & (targets == c)).sum().float()
        fp = ((predicted == c) & (targets != c)).sum().float()
        fn = ((predicted != c) & (targets == c)).sum().float()
        precision = tp / (tp + fp + 1e-8)
        recall = tp / (tp + fn + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        weighted_f1 += f1.item() * (support.item() / total)
    return weighted_f1


def _exact_accuracy(preds: Tensor, targets: Tensor) -> float:
    """Exact scoreline accuracy: both home and away goals correct."""
    pred_home = preds[:, 0, :].argmax(dim=-1)
    pred_away = preds[:, 1, :].argmax(dim=-1)
    target_home = targets[:, 0]
    target_away = targets[:, 1]
    correct = (pred_home == target_home) & (pred_away == target_away)
    return correct.float().mean().item()


def _mae_goals(preds: Tensor, targets: Tensor) -> float:
    """Mean absolute error for goal predictions."""
    pred_home = preds[:, 0, :].argmax(dim=-1).float()
    pred_away = preds[:, 1, :].argmax(dim=-1).float()
    target_home = targets[:, 0].float()
    target_away = targets[:, 1].float()
    mae = (
        (pred_home - target_home).abs().mean()
        + (pred_away - target_away).abs().mean()
    ) / 2
    return mae.item()


def _mae(preds: Tensor, targets: Tensor) -> float:
    return (preds - targets).abs().mean().item()


def _mse(preds: Tensor, targets: Tensor) -> float:
    return ((preds - targets) ** 2).mean().item()


def _r2(preds: Tensor, targets: Tensor) -> float:
    ss_res = ((targets - preds) ** 2).sum()
    ss_tot = ((targets - targets.mean()) ** 2).sum()
    return (1 - ss_res / (ss_tot + 1e-8)).item()


# Registry: metric_name -> compute function
_METRIC_FNS: dict[str, callable] = {
    "accuracy": _accuracy,
    "f1_macro": _f1_macro,
    "f1_weighted": _f1_weighted,
    "exact_accuracy": _exact_accuracy,
    "mae_goals": _mae_goals,
    "mae": _mae,
    "mse": _mse,
    "r2": _r2,
}

# Available metrics per head type
METRIC_REGISTRY: dict[str, list[str]] = {
    "match_outcome": ["accuracy", "f1_macro", "f1_weighted"],
    "scoreline": ["exact_accuracy", "mae_goals"],
    "player_stat": ["mae", "mse", "r2"],
    "match_stat": ["mae", "mse", "r2"],
}


def compute_metrics(
    head_type: str,
    predictions: Tensor,
    targets: Tensor,
    metric_names: list[str] | None = None,
) -> dict[str, float]:
    """Compute metrics for a prediction head.

    Args:
        head_type: prediction head type.
        predictions: model output tensor.
        targets: ground truth tensor.
        metric_names: which metrics to compute. If None, computes all
            available for the head type.

    Returns:
        Dict of metric_name -> value.
    """
    available = METRIC_REGISTRY.get(head_type, [])
    names = metric_names or available
    names = [n for n in names if n in available]

    results = {}
    for name in names:
        fn = _METRIC_FNS.get(name)
        if fn:
            results[name] = fn(predictions.detach(), targets.detach())
    return results


def get_available_metrics() -> dict[str, list[str]]:
    """Return available metrics per head type."""
    return dict(METRIC_REGISTRY)
