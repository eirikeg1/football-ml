# Search journal

One block per iteration. Append, never rewrite history.

---

## iter-NNN — <YYYY-MM-DD HH:MM>

**Phase:** A (broad) | B (refine) | C (multi-seed) | D (full) | E (test) | F (report)
**Hypothesis tested:** <which part of HYPOTHESIS.md this iteration probes>
**Delta from baseline:** <summarize the diff: which params changed and to what>
**Rationale:** <why this delta is worth testing — one line>

**Result:**
- best_metric: <value or "crashed">
- val_loss: <value>
- epochs run: <N>
- elapsed: <seconds>
- gpu peak util: <%>

**Verdict:** <one sentence: was the hypothesis supported? new finding? null result?>

**Follow-up:** <what this implies for the next iteration>
