"""Pre-launch GPU check.

Returns a structured verdict so the CLI can refuse to launch when another
process is already saturating the card. Defaults are conservative; pass
`force=True` to ignore them.
"""

from __future__ import annotations

from dataclasses import dataclass

from football_ml.utils.gpu_monitor import _sample_once


@dataclass
class PreflightVerdict:
    ok: bool
    reason: str
    sample: dict | None


def preflight(
    max_util_pct: int = 30,
    max_mem_used_mb: int = 2000,
    force: bool = False,
) -> PreflightVerdict:
    """Decide whether it's safe to launch a training run.

    Refuses when the GPU is currently busier than the thresholds. Always allows
    if nvidia-smi is unavailable (assumes CPU-only or non-NVIDIA host).
    """
    sample = _sample_once()
    if sample is None:
        return PreflightVerdict(True, "nvidia-smi unavailable; skipping preflight", None)
    if force:
        return PreflightVerdict(True, "preflight bypassed via force=True", sample)
    util = sample["util_pct"]
    mem = sample["mem_used_mb"]
    if util > max_util_pct or mem > max_mem_used_mb:
        return PreflightVerdict(
            False,
            f"GPU busy: util={util}% (>{max_util_pct}%), "
            f"mem_used={mem}MB (>{max_mem_used_mb}MB). "
            f"Wait for the current run, or pass --force to override.",
            sample,
        )
    return PreflightVerdict(True, "GPU idle", sample)
