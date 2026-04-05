# Architecture Overview

## Pipeline Design Philosophy

The pipeline follows a **modular, layered architecture** where each component has clean interfaces, allowing individual modules to be swapped, disabled, or reconfigured without affecting the rest of the pipeline.

## Pipeline Layers

```
Layer 1: Feature Extractors (pretrained, modular, swappable)
  ├── PlayerProfileEncoder    [FM stats → embedding]
  ├── PlayerFormEncoder       [recent stats → embedding]
  ├── TeamPerformanceEncoder  [team stats + xG + Elo → embedding]
  └── MatchContextEncoder     [home/away, rest days, competition, schedule → embedding]

Layer 2: Composition (relational structure)
  └── LineupGNN               [player embeddings + formation graph → team embedding]
      (one per team in the match)

Layer 3: Fusion (cross-feature interaction)
  └── TransformerEncoder      [all embeddings as tokens → unified match representation]

Layer 4: Temporal (dynamics over match sequences)
  └── GRU / alternatives      [sequence of match representations → temporal state]

Layer 5: Prediction Heads (task-specific, swappable)
  ├── MatchOutcomeHead        [W/D/L probabilities]
  ├── ScorelineHead           [goal distributions]
  ├── PlayerStatHead          [individual player predictions]
  └── MatchStatHead           [team-level stat predictions]
```

## Modularity Principles

- **Clean interfaces between layers**: each layer produces a fixed-size embedding/tensor, so downstream layers don't care what produced it.
- **Swappable components**: any module can be replaced with an alternative implementation behind the same interface.
- **Optional modules**: disabling a feature module (e.g., removing the PlayerProfileEncoder) should not break the pipeline — the fusion layer handles variable numbers of input tokens naturally.
- **Independent pretraining**: feature extractors (Layer 1) can be pretrained separately on their own objectives before being plugged into the full pipeline.
