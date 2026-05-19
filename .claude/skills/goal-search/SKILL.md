---
name: goal-search
description: |
  Use this skill whenever the user invokes /goal with an ML training/search
  intent in this repository, or asks you to "find the best config",
  "optimize hyperparameters", "search for a pipeline that achieves X", or
  similar. It codifies a tournament-style search loop on top of the
  football-ml training CLI: short broad runs first, then targeted refinement,
  multi-seed validation, full training of finalists, a gated test-set
  evaluation, and a final report with graphs.
---

# goal-search — playbook

You are running an autonomous-but-checkpointed ML pipeline search using
Claude Code's `/goal` iterative loop. Read this entire skill before the
first iteration. Follow the rules exactly — they exist because the user
has been burned by past mistakes (test-set peeking, runaway full runs,
incoherent searches that drift without a hypothesis).

## 1. Setup ritual (run ONCE at the start of every `/goal` session)

1. **Confirm intent.** Restate the goal in one sentence and ask for the
   baseline YAML path. Do NOT default to a canonical baseline; the user
   wants explicit per-search choice. Example prompt:
   > "Search goal: maximize val match_outcome accuracy in ≤30 smoke
   > iterations. Which YAML should I use as the baseline? (e.g.,
   > `configs/examples/01-minimal-hetero-gnn.yaml`)"
2. **Pick a split strategy.** Look at the dataset and goal and propose one
   of `latest_season_per_competition` (default for football), `time_percentile`,
   `season_year`, or `random_seeded` (ablation only). State the proposed
   strategy + params and confirm with the user before continuing.
3. **Create the results directory:**
   ```
   results/<YYYY-MM-DD-HHMM>_<goal-slug>/
   ```
   Slug = first 4–6 lowercase words of the goal, dashes only.
4. **Write the starter files** using the templates in this skill:
   - `GOAL.md` — verbatim user goal, agreed termination condition, iteration
     cap, split strategy + params.
   - `HYPOTHESIS.md` — initial "I don't know yet" placeholder; will be
     overwritten per iteration.
   - `JOURNAL.md` — empty header.
   - `DEAD_ENDS.md` — empty header.
   - `NUDGES.md` — instructions for the user on how to inject mid-search
     guidance.
   - Copy baseline YAML to `<results>/baseline.yaml`.
5. **Sanity check** by running:
   ```bash
   python -m football_ml.cli.train \
       --config <results>/baseline.yaml \
       --run-dir /tmp/preflight-check \
       --validate-only --force
   ```
   If it fails, surface the error and stop — fixing the baseline is
   prerequisite work, not part of the search.

## 2. Per-iteration loop

Each iteration follows this exact sequence. Do not skip steps.

1. **Read state.** `cat` the current `JOURNAL.md`, `HYPOTHESIS.md`,
   `NUDGES.md`, and `python -m football_ml.search.leaderboard <results>`.
   If the user appended to `NUDGES.md` since the last iteration, treat it as
   the highest-priority signal.
2. **Decide what to try.** Pick a config delta with explicit rationale.
   Reference the current hypothesis. Reject anything already on the
   leaderboard (config hash collision) unless you're deliberately
   reproducing for variance estimation.
3. **Write the candidate config:**
   ```
   <results>/runs/iter-NNN/config.yaml
   ```
   `NNN` = zero-padded counter. The CLI itself writes `config.yaml` as a
   verbatim copy of `--config`, so just ensure you've prepared the file
   you'll pass.
4. **Preflight GPU check.** Always. Never skip.
5. **Launch in background** with the Monitor tool:
   ```bash
   python -m football_ml.cli.train \
       --config <results>/runs/iter-NNN/config.yaml \
       --run-dir <results>/runs/iter-NNN \
       --smoke --gpu-monitor
   ```
   For non-smoke phases, omit `--smoke` and use the user-confirmed setting.
6. **Poll `status.json`** every 5–15 seconds. Read `phase`, `current_epoch`,
   `finished`. When `finished=true`, proceed; the Monitor tool will also
   notify you when the process exits.
7. **Update state:**
   - Append an entry to `JOURNAL.md` (use the journal template).
   - If the run crashed (`exit_code != 0`) or hit NaN, append a one-line
     entry to `DEAD_ENDS.md` with the root cause.
   - Every 5 iterations (or sooner if a clear pattern emerges), rewrite
     `HYPOTHESIS.md` to reflect what's actually been learned.

## 3. Tournament strategy (phases A → F)

Default budgets — adjust based on the iteration cap in `GOAL.md`.

### Phase A — Broad exploration (≈15–20 iterations, smoke mode)

- Vary **multiple axes per iteration** to cover the space cheaply.
- Smoke defaults: `--smoke` (uses `max_samples=1000`, `max_epochs=5`).
- Deliberately try **architecturally distinct** approaches every 5–10
  iterations (e.g., swap hetero_gnn for flat, try without history sequence,
  flip the head). Stops the search from converging on a basin too early.
- Keep top 40% by best val metric → "survivors".

### Phase B — Targeted refinement (≈5–8 iterations per survivor)

- For each survivor, perturb **one axis at a time**.
- Slightly longer smoke: pass `--max-samples 3000 --max-epochs 10`.
- Keep top 5 → finalists candidates.

### Phase C — Multi-seed validation (3 seeds × 5 candidates)

- Use `python -m football_ml.search.multi_seed <iter-dir> --seeds 3 --smoke`.
- Compute mean ± stdev for each candidate.
- Keep the 2–3 with **both** high mean **and** low stdev. A high-variance
  candidate is probably lucky, not good.

### Phase D — Full training of finalists (GATED)

- **Ask the user before launching.** Show the candidate list with their
  multi-seed numbers. Confirm before running.
- Drop `--smoke` and any `--max-samples` / `--max-epochs` overrides.
- Each finalist gets one full-data run under `<results>/finalists/`.

### Phase E — Test-set evaluation (GATED, ONCE)

- **Ask the user before launching.** Confirm exactly which finalist to
  evaluate. After this step, the test set is "burned" for this search —
  do not propose further iterations that consult it.
- Run:
  ```bash
  python -m football_ml.cli.test_eval --run-dir <finalist-run-dir>
  ```
- Results land in `<finalist-run-dir>/test-eval-results.json`.

### Phase F — Report

- Run `python -m football_ml.search.report <results>`.
- Open the generated `SEARCH_REPORT.md`, read the figures, and **append a
  qualitative insights section**: what worked, what didn't, surprising
  patterns, recommendations for the next search. The report's auto-section
  is the data; your appended section is the synthesis.

## 4. Periodic self-review (every 5 iterations during phases A/B)

Re-read `JOURNAL.md` + leaderboard + `DEAD_ENDS.md`. Ask yourself:

- Which knobs are correlated with the best runs? (Update `HYPOTHESIS.md`.)
- Which knobs seem to make no difference? (Stop varying them.)
- Are crashes clustering on a particular setting? (Add to `DEAD_ENDS.md`.)
- Am I drifting from the goal? (Re-read `GOAL.md`.)

If you don't have anything to update, write that explicitly: "iter 15 review:
no new patterns, continuing current hypothesis." Forces honest accounting.

## 5. Anti-patterns (do not do these)

- **Never look at test-set metrics during search.** The test-set CLI is
  designed to be invoked once; don't peek by running it mid-search.
- **Never launch a non-smoke run without user confirmation** (Phases D and
  E only). Auto-launching is for smoke runs and multi-seed only.
- **Never skip the GPU preflight.** If preflight refuses, wait or surface
  the problem to the user. Do not pass `--force` unprompted.
- **Never keep checkpoints from non-survivor runs.** After each phase, delete
  `checkpoint.pt` from runs that didn't make the cut to save disk.
- **Don't converge too fast.** Phase A must include genuinely distinct
  approaches, not just incremental perturbations.
- **Don't invent metrics.** The goal must be measurable from
  `metrics.jsonl` or `test-eval-results.json`. If you can't articulate the
  measurement, stop and ask the user.
- **Don't fabricate journal entries.** If a run failed, say so. Negative
  results are the whole point of `DEAD_ENDS.md`.

## 6. Useful commands

```bash
# Print current leaderboard
python -m football_ml.search.leaderboard <results> --format md

# Save leaderboard.md + leaderboard.jsonl into the results dir
python -m football_ml.search.leaderboard <results> --save

# Multi-seed validation
python -m football_ml.search.multi_seed <results>/runs/iter-NNN --seeds 3 --smoke

# Final report
python -m football_ml.search.report <results>

# Test-set eval (once, gated)
python -m football_ml.cli.test_eval --run-dir <results>/finalists/iter-NNN
```

## 7. Templates

The four starter files use the templates in `templates/` next to this skill.
Copy them verbatim and fill in the placeholders. Re-read them — they encode
the structure each file needs to maintain across iterations.

- `templates/GOAL.md`
- `templates/HYPOTHESIS.md`
- `templates/JOURNAL.md` (entry format — append one block per iteration)
- `templates/SEARCH_REPORT.md` (skeleton; auto-report fills in figures)
- `templates/NUDGES.md`

## 8. Termination conditions

Stop the search loop when **any** of these is true:

- The goal's success criterion is met (e.g., val metric ≥ target).
- The iteration cap in `GOAL.md` is reached.
- 10 consecutive iterations show no improvement over the current best.
- The user pauses or interrupts.

After termination, run Phases D/E/F (if not already done). Write the final
report. Tell the user where to look.
