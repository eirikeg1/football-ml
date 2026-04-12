# Heterogeneous GNN Strategy for Relational Football Data

## Overview

Replace the current multi-stage pipeline (feature extractors → LineupGNN → fusion)
with a single Heterogeneous Graph Transformer (HGT) that operates directly on the
relational database structure. Each database table becomes a node type, each foreign
key becomes an edge type. The GNN learns entity representations through message
passing across the full relational graph.

Temporal causality is enforced through **rolling snapshot graphs**: for each prediction
point, only historical data is included in the graph.

---

## 1. Graph Structure

### Node Types and Features

| Node Type       | Source Table    | Count   | Features (numeric)                                                                 |
|-----------------|----------------|---------|------------------------------------------------------------------------------------|
| `match`         | matches         | 13,877  | kickoff_time, home_score, away_score, matchday                                     |
| `match_stat`    | match_stats     | 19,528  | possession, pass_accuracy, total_passes, shots, shots_on_target, corners, fouls, yellow_cards, red_cards, offsides, saves |
| `match_event`   | match_events    | 185,393 | minute, extra_minute, event_type (one-hot encoded)                                 |
| `team`          | teams           | 84      | (learned embedding — no meaningful numeric features in this table)                 |
| `competition`   | competitions    | 2       | (learned embedding — type only)                                                    |

**Notes:**
- `team` and `competition` nodes have no useful numeric features (just names/countries).
  Use **learnable embedding vectors** initialized randomly, trained end-to-end.
- `match_event.event_type` is categorical (7 values: goal, yellow_card, red_card,
  second_yellow, substitution, penalty, own_goal) → one-hot encode to 7-dim vector.
- `match.home_score` and `match.away_score` are features for historical matches
  but are the **prediction targets** for the target match (excluded from its features).

### Edge Types (from FK relationships)

| Edge Type                                    | From → To                  | Count    | Semantics                        |
|----------------------------------------------|----------------------------|----------|----------------------------------|
| `(match_stat, stat_of, match)`               | match_stats.match_id → matches.id | 19,528   | "this stat row belongs to this match" |
| `(match_stat, by_team, team)`                | match_stats.team_id → teams.id   | 19,528   | "this stat row is for this team"  |
| `(match_event, event_in, match)`             | match_events.match_id → matches.id | 185,393 | "this event happened in this match" |
| `(match_event, event_by, team)`              | match_events.team_id → teams.id  | 185,393  | "this event involved this team"   |
| `(match, home_team, team)`                   | matches.home_team_id → teams.id  | 13,877   | "home team of this match"         |
| `(match, away_team, team)`                   | matches.away_team_id → teams.id  | 13,877   | "away team of this match"         |
| `(match, in_competition, competition)`       | matches.competition_id → competitions.id | 13,877 | "match played in this competition" |

**Reverse edges:** For each edge type above, add the reverse direction (e.g.,
`(team, home_of, match)`, `(match, has_stat, match_stat)`) to enable bidirectional
message passing. This doubles the edge types to 14.

### Full Graph Visualization

```
competition ←── in_competition ── match ── home_team ──→ team
                                   ↑  ↑                    ↑
                          stat_of ─┘  └─ event_in          │
                             │              │              │
                         match_stat    match_event ─ event_by
                             │
                          by_team ──────────────────→ team
```

---

## 2. Model Architecture

### HeteroGNN Module

Based on PyTorch Geometric's `HGTConv` (Heterogeneous Graph Transformer).

```
Input: HeteroData with 5 node types, 14 edge types

Per-node-type input projection:
  match:       Linear(4 → d_model)        # 4 numeric features
  match_stat:  Linear(11 → d_model)       # 11 stat features
  match_event: Linear(9 → d_model)        # minute + extra_minute + 7-dim one-hot
  team:        Embedding(84, d_model)      # learned, no raw features
  competition: Embedding(2, d_model)       # learned, no raw features

HGTConv layers × L:
  Each layer does per-edge-type attention + message passing
  All node types updated in parallel

Readout: extract team node embeddings → combine for match prediction
```

### Recommended Hyperparameters (starting point)

| Parameter    | Value | Rationale                                    |
|--------------|-------|----------------------------------------------|
| `d_model`    | 128   | Shared hidden dim across all node types      |
| `num_heads`  | 8     | HGT attention heads                          |
| `num_layers` | 3     | Sufficient depth for 2-hop message passing   |
| `dropout`    | 0.2   | Regularization                               |

### Team-Level Readout

For predicting match M between team A and team B:

1. Run HeteroGNN on the snapshot graph → get all `team` node embeddings
2. Extract `team_A_embed` and `team_B_embed`
3. Concatenate: `match_repr = [team_A_embed; team_B_embed]` (2 × d_model)
4. Optionally include competition embedding and match context features

This produces a (2 × 128 = 256)-dimensional match representation per prediction.

### Integration with Temporal Model

```
For each match to predict (in chronological order):
  1. Build rolling snapshot graph (history up to this match)
  2. Run HeteroGNN → team embeddings
  3. Combine team_A + team_B → match_repr

Collect last N match_reprs for each team → sequence
Feed sequence to GRU temporal model → temporal_state
Prediction head(temporal_state) → outcome/scoreline/stats
```

The existing `GRUTemporal` and prediction heads remain unchanged.
Only the upstream (feature extraction + composition + fusion) is replaced by the HeteroGNN.

---

## 3. Rolling Snapshot Construction

### Per-Matchday Precomputation

Instead of rebuilding the graph for every single match, precompute one snapshot
per **matchday** (or per calendar date). All matches on the same date share the
same historical graph.

**Algorithm:**

```python
# Sort all matches by kickoff_time
matches_sorted = matches.sort_values("kickoff_time")

# Group by matchday/date
for matchday, target_matches in matches_sorted.groupby("matchday_date"):
    # Historical cutoff: everything before this matchday
    hist_matches = matches[matches.kickoff_time < matchday_start_time]
    hist_match_ids = set(hist_matches.id)

    # Filter stats and events to only historical matches
    hist_stats = match_stats[match_stats.match_id.isin(hist_match_ids)]
    hist_events = match_events[match_events.match_id.isin(hist_match_ids)]

    # All teams and competitions are always included (they're entities, not events)
    snapshot = build_hetero_graph(hist_matches, hist_stats, hist_events, teams, competitions)

    # For each target match on this matchday:
    for match in target_matches:
        team_a_idx = team_id_to_node_idx[match.home_team_id]
        team_b_idx = team_id_to_node_idx[match.away_team_id]
        yield snapshot, team_a_idx, team_b_idx, labels(match)
```

**Snapshot count:** ~380 matchdays/season × 18 seasons ≈ 6,840 snapshots.
Early-season snapshots are small; late-season snapshots are large.

### Memory Management

Full graph at peak: ~220k nodes, ~460k edges (with reverse edges).
This fits comfortably in GPU memory as a single HeteroData object.

For the rolling snapshots, early matchdays have very few nodes. As the
dataset grows, the later snapshots approach the full graph size.

**Options for scaling:**
- **Full batch per snapshot** (feasible for this dataset size — ~220k nodes is small for GNNs)
- **Neighbor sampling** via `HGTLoader` if memory becomes an issue with larger datasets
- **Cache HeteroData objects** to disk (e.g., torch.save) to avoid reconstruction during training

---

## 4. Training Procedure

### Data Split

Split by time, not randomly:
- **Train:** Seasons 2008-2022 (~11,000 matches)
- **Validation:** Season 2023 (~760 matches)
- **Test:** Seasons 2024-2025 (~1,500 matches)

### Training Loop

```python
for epoch in range(num_epochs):
    for snapshot, team_a_idx, team_b_idx, targets in train_loader:
        # 1. Forward pass through HeteroGNN
        node_embeddings = hetero_gnn(snapshot)  # dict of {node_type: Tensor}
        team_embeds = node_embeddings["team"]

        # 2. Extract team embeddings for this match
        team_a_emb = team_embeds[team_a_idx]
        team_b_emb = team_embeds[team_b_idx]

        # 3. Build match representation
        match_repr = torch.cat([team_a_emb, team_b_emb], dim=-1)

        # 4. (Optional) Temporal: collect recent match_reprs into sequence
        # ... feed to GRU ...

        # 5. Prediction + loss
        pred = head(match_repr)  # or head(temporal_state)
        loss = criterion(pred, targets)
        loss.backward()
        optimizer.step()
```

### Loss Functions

Same as current pipeline heads:
- **Match outcome:** CrossEntropyLoss (3 classes: home win, draw, away win)
- **Scoreline:** Two independent CrossEntropyLoss (home goals, away goals)
- **Match stats:** MSELoss (predict possession, shots, etc.)

Multi-task training: weighted sum of losses from multiple heads.

---

## 5. Event Node Handling

Match events (185k nodes) are the most numerous. Two approaches:

### Option A: Include all events as nodes (default)

Every event is a node in the graph. The GNN aggregates event information into
match nodes (via `event_in` edges) and team nodes (via `event_by` edges).

**Pros:** Maximum information preserved, GNN can learn event patterns.
**Cons:** Largest graph size, slower training.

### Option B: Pre-aggregate events into match-level features

Instead of 185k event nodes, compute per-match event counts:
- goals_scored, goals_conceded, yellow_cards, red_cards, penalties, substitutions
- Per-team per-match aggregation → additional features on match_stat nodes

**Pros:** Much smaller graph (~33k nodes instead of ~220k), faster training.
**Cons:** Loses minute-level event granularity.

**Recommendation:** Start with Option B (pre-aggregated) for faster iteration.
Add Option A as a configuration flag once the core architecture works.

---

## 6. Implementation Plan

### New Files

| File | Purpose |
|------|---------|
| `src/football_ml/composition/hetero_gnn.py` | HeteroGNN module using HGTConv |
| `src/football_ml/datasource/snapshot.py` | Rolling snapshot graph construction |
| `src/football_ml/datasource/graph_features.py` | Feature encoding (one-hot events, embeddings) |
| `src/football_ml/pipeline_hetero.py` | HeteroGNN pipeline (alternative to pipeline.py) |
| `configs/hetero-gnn.yaml` | Default config for the HeteroGNN pipeline |
| `tests/smoke/test_hetero_gnn.py` | Smoke tests for HeteroGNN forward pass |

### Modified Files

| File | Change |
|------|--------|
| `src/football_ml/config.py` | Add `HeteroGNNConfig` dataclass |
| `src/football_ml/datasource/materialize.py` | Improve `to_hetero_graph()` with reverse edges, learned embeddings support |
| `webapp/src/lib/registry.ts` | Add `hetero_gnn` node type to composition category |

### Implementation Order

1. **HeteroGNN module** — HGTConv-based model with per-type projections
2. **Snapshot construction** — rolling temporal graph builder
3. **Feature encoding** — one-hot events, learned entity embeddings
4. **HeteroGNN pipeline** — end-to-end forward pass
5. **Training loop** — data loading, loss, optimization
6. **Smoke tests** — verify shapes and forward pass
7. **Webapp node** — add to registry, wire to materialization panel

---

## 7. Configuration

```yaml
hetero_gnn:
  d_model: 128
  num_heads: 8
  num_layers: 3
  dropout: 0.2
  include_events: false        # Option A vs B toggle
  readout: "team_concat"       # how to combine team embeddings
  team_embed_dim: 128          # learned embedding for teams
  competition_embed_dim: 32    # learned embedding for competitions

snapshot:
  strategy: "per_matchday"     # or "per_date", "per_week"
  min_history_matches: 10      # skip prediction if team has < N historical matches

temporal:
  type: "gru"
  input_dim: 256               # 2 × d_model (team_a + team_b concat)
  hidden_dim: 128
  output_dim: 128
  seq_len: 10                  # last 10 matches per team
```
