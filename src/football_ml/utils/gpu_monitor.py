"""Background nvidia-smi sampler.

Polls `nvidia-smi` at a configurable interval and appends JSONL lines to
`<run_dir>/gpu.jsonl`. Started by the training CLI when `--gpu-monitor` is
set; stopped at exit. Silently no-ops if nvidia-smi is unavailable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from pathlib import Path


_QUERY = "utilization.gpu,memory.used,memory.total,temperature.gpu"


def _sample_once() -> dict | None:
    """Return one sample dict or None if nvidia-smi is unavailable / failed."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={_QUERY}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None

    # First GPU only — the 3090 is single-card. Extending to multi is trivial.
    first = out.splitlines()[0] if out else ""
    parts = [p.strip() for p in first.split(",")]
    if len(parts) < 4:
        return None
    try:
        return {
            "ts": time.time(),
            "util_pct": int(parts[0]),
            "mem_used_mb": int(parts[1]),
            "mem_total_mb": int(parts[2]),
            "temp_c": int(parts[3]),
        }
    except ValueError:
        return None


class GpuMonitor:
    """Sample nvidia-smi every `interval` seconds, writing JSONL to `path`."""

    def __init__(self, path: Path | str, interval: float = 5.0) -> None:
        self.path = Path(path)
        self.interval = max(0.5, float(interval))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="gpu-monitor")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 1.0)
            self._thread = None

    def _loop(self) -> None:
        # Append mode so a resumed run extends the timeline rather than clobbering it.
        with self.path.open("a", buffering=1) as f:
            while not self._stop.wait(self.interval):
                sample = _sample_once()
                if sample is None:
                    continue
                f.write(json.dumps(sample) + "\n")
