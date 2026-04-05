# Experimentation Notes

Design and ideation documentation for the football statistics prediction pipeline.

## Contents

1. [Architecture Overview](01-architecture-overview.md) — Pipeline layers, modularity principles
2. [Feature Taxonomy](02-feature-taxonomy.md) — How features are categorized by granularity and volatility
3. [Feature Extractors](03-feature-extractors.md) — Layer 1 design, pretraining strategies (multi-task, contrastive, autoencoder)
4. [Composition and Fusion](04-composition-and-fusion.md) — Lineup GNN (Layer 2) and fusion options A/B/C (Layer 3)
5. [Temporal Modeling](05-temporal-modeling.md) — GRU-based temporal layer, time gap handling, season boundaries
6. [Prediction Heads](06-prediction-heads.md) — Task-specific output layers (outcomes, scores, stats)
7. [Data Sources](07-data-sources.md) — Available and recommended data sources
8. [Existing Work](08-existing-work.md) — Prior work, tools, and libraries to build upon

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| First fusion approach | Transformer Encoder (Option B) | Variable token count fits modularity; learns cross-feature interactions |
| First temporal model | GRU | Simple, proven, lightweight |
| Player profile pretraining | Multi-task (position + value) | Natural targets available, straightforward |
| GNN framework | PyTorch Geometric | Standard, well-supported |
| Pipeline philosophy | Modular, swappable components | Experimentation-focused project |
