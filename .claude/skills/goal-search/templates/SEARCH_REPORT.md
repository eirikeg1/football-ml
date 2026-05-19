# Search report skeleton

`python -m football_ml.search.report <results>` regenerates this file with
the latest data. Append your **qualitative insights** below the auto-generated
sections — the auto-section is the data; your synthesis is the value.

The auto-section will include:

- Goal (copied from GOAL.md)
- Final hypothesis (copied from HYPOTHESIS.md)
- Leaderboard (top to bottom by best val metric)
- Figures (metric vs iteration, top-K loss curves, hyperparameter
  sensitivity boxplots, GPU utilization timeline)
- Dead ends (copied from DEAD_ENDS.md)
- Test-set evaluation (if Phase E was run)

After re-running the report, append:

## Insights & recommendations

- What worked, what didn't, what surprised me.
- Three concrete things I'd try if given another budget.
- Open questions the search couldn't answer (e.g., "did not explore X
  because of cost").

## Reproducibility checklist

- [ ] Each finalist's `run_meta.json` records git SHA, deps, dataset
      snapshot, seed, split strategy, split params.
- [ ] Test-set evaluation was run exactly once.
- [ ] `baseline.yaml` is the actual starting point referenced in the report.
