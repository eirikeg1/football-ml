# Goal

**Started:** <YYYY-MM-DD HH:MM>
**Baseline:** `<path/to/baseline.yaml>`
**Iteration cap:** <N>

## User's goal (verbatim)

> <paste the user's verbatim goal string here>

## Termination conditions

- Success: <measurable criterion, e.g., "val match_outcome accuracy ≥ 0.55">
- Iteration cap: <N>
- Plateau: 10 consecutive iterations without improvement
- User interrupt

## Split strategy

- **Strategy:** `<latest_season_per_competition | time_percentile | season_year | random_seeded>`
- **Params:** `<JSON>`
- **Rationale:** <one-line justification>

## Headline metric

- **Name:** `<accuracy | f1_macro | mae | ...>` (the first metric in `training.metrics`)
- **Direction:** maximize / minimize
- **Source:** `metrics.jsonl[*].metrics.<name>`

## Test-set discipline

- The test set is scored exactly once, at the end of the search, on one finalist.
- Until that one call, no iteration may consult test metrics.
- The test-set CLI: `python -m football_ml.cli.test_eval --run-dir <finalist-run-dir>`.
