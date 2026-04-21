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

## Testing

```bash
# Run all tests
pytest

# Run by category
pytest -m smoke          # Forward pass sanity checks for every module
pytest -m integration    # Multi-module combination tests
pytest tests/unit/       # Config loading, base class contracts
```
