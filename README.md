# Football ML

A modular machine learning pipeline for predicting football match statistics and outcomes. Built for experimentation — components can be swapped, reconfigured, and extended independently.

## Pipeline Editor
![Pipeline editor screenshot](resources/images/pipeline-editor.png)

The editor is a Svelte app in [`webapp/`](webapp/). Requires Node.js.

```bash
cd webapp
npm install           # first time only
npm run dev           # start dev server at http://localhost:5173/
npm run build         # production build to webapp/dist/
npm run preview       # serve the built bundle
```

The **Training** tab talks to a Python backend over `/api` and `/ws/training` (proxied by Vite to `http://127.0.0.1:8000`). Start it in a second terminal (activate the venv first — see [Setup](#setup)):

```bash
source .venv/bin/activate
python -m football_ml.server
```

Without it the Training view stays in the `disconnected` state; the UI auto-reconnects every 3s once the server is up.

## Setup

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```python
from football_ml.config import load_config
from football_ml.pipeline import FootballPipeline

config = load_config("configs/default.yaml")
pipeline = FootballPipeline(config, head="match_outcome")
```

Pipeline configuration is driven by YAML files — see [`configs/default.yaml`](configs/default.yaml) for the full set of options.

## Batch training CLI

For single-run training to disk (used by the `/goal` search loop, not the
webapp), use the batch CLI:

```bash
python -m football_ml.cli.train \
    --config configs/examples/01-minimal-hetero-gnn.yaml \
    --run-dir results/scratch/run-1 \
    --smoke --gpu-monitor
```

Outputs land in `--run-dir`: `config.yaml`, `metrics.jsonl`, `status.json`,
`log.txt`, `gpu.jsonl`, `run_meta.json`, and `checkpoint.pt` (when the best
epoch is updated). Add `--validate-only` to parse and build the model
without training.

## Goal-driven search

`/goal` (built-in in Claude Code 2.1.139+) plus the `goal-search` skill in
[`.claude/skills/goal-search/`](.claude/skills/goal-search/SKILL.md) drives a
tournament-style hyperparameter search: broad smoke runs first, then refined
exploration, multi-seed validation, gated full training, one-shot test-set
evaluation, and a final report. Results land in `results/<timestamp>_<slug>/`
with a structured directory layout. The skill prompts for a baseline YAML and
split strategy at the start of every session.

Helper CLIs (also exposed as console entry points via `pip install -e .`):

- `python -m football_ml.search.leaderboard <results-dir>`
- `python -m football_ml.search.multi_seed <iter-dir> --seeds 3`
- `python -m football_ml.search.report <results-dir>`
- `python -m football_ml.cli.test_eval --run-dir <finalist-run-dir>`

## Testing

```bash
# Run all tests
pytest

# Run by category
pytest -m smoke          # Forward pass sanity checks for every module
pytest -m integration    # Multi-module combination tests
pytest tests/unit/       # Config loading, base class contracts
```
