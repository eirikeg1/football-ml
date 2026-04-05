# Existing Work and References

Relevant prior work and tools that can be built upon or used as features/baselines.

## Player Representations

### Player Vectors (Decroos & Davis)
- Learn player representations from action sequences
- Different angle from FM stats but complementary — based on what players actually do on the pitch
- Could be used as an alternative or additional player embedding source

### Football Manager Attribute Embeddings
- No widely adopted standard approach, but the multi-task pretraining approach (predict position + value from attributes) is well-established in representation learning literature

## Team and Match Modeling

### Graph Neural Networks in Football
- Recent work on using GNNs for formation analysis and team representation
- PyTorch Geometric provides all building blocks
- Graph structure: players as nodes, edges for positional/passing relationships

### Elo Rating Systems
- Club Elo (clubelo.com) — continuously updated team ratings
- Well-understood, hard-to-beat baseline for match outcome prediction
- Include as feature rather than trying to replace

## Frameworks and Libraries

### socceraction (KU Leuven)
- Open-source library for football analytics
- Implements VAEP (Valuing Actions by Estimating Probabilities)
- Could feed into player form features

### PyTorch Geometric
- Selected framework for GNN components
- Provides message passing, graph convolution, pooling layers

## Metrics and Evaluation

### Expected Goals (xG)
- Widely available, well-validated metric
- Use as both a feature and a potential evaluation reference
- Multiple open-source implementations exist
