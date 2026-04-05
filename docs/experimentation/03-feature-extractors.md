# Feature Extractors

Feature extractors (Layer 1) transform raw data into learned representations. They can be pretrained independently before plugging into the full pipeline.

## PlayerProfileEncoder

**Input**: Football Manager attribute vectors (~30-50 scalar attributes per player)

**Goal**: Produce an embedding that captures player quality and positional/type profile.

### Pretraining Approaches

#### Multi-task Pretraining (recommended starting point)
Train a small MLP (3-4 layers) to simultaneously predict:
- Player position(s)
- Market value
- Age bracket
- League level

The intermediate layers must encode "what kind of player is this" to solve all tasks at once. After training, extract the embedding from a middle layer.

**Why MLP over CNN/Transformer**: FM stats are tabular (not spatial or sequential), so a plain MLP is the natural fit. Save architectural complexity for where structure exists.

#### Contrastive Learning
Train the encoder so similar players map to nearby points in embedding space:
1. Define similarity: same position cluster, similar value band, similar playing style
2. Use SimCLR, triplet loss, or similar contrastive objective
3. Result: rich embeddings without needing specific prediction targets

**Complementary to multi-task** — can pretrain with multi-task, then fine-tune with contrastive, or combine as joint loss terms.

#### Autoencoder
Compress FM attributes to a bottleneck and reconstruct. Simplest approach, good as a quick baseline.

### Design Rationale

The key insight is that FM attributes have an "update lag" — they're a pre-season snapshot. By combining the FM-derived profile embedding with **current season form data** (from PlayerFormEncoder), the pipeline gets both:
- **Player type/quality** (stable, from FM)
- **Current performance level** (dynamic, from match data)

These combined player features feed into the LineupGNN.

## PlayerFormEncoder

**Input**: Sequence of recent match statistics for a player (goals, assists, minutes, ratings, etc.)

**Output**: Form embedding capturing current performance trajectory

Possible architectures: small GRU/LSTM over recent N matches, or windowed MLP.

## TeamPerformanceEncoder

**Input**: Team-level statistics including xG, xGA, possession, points, Elo rating, Club Elo

**Output**: Team performance embedding

Elo and Club Elo are strong baselines for team strength and should be included as features.

## MatchContextEncoder

**Input**: Contextual scalars — home/away flag, competition type, rest days, schedule density, etc.

**Output**: Context embedding

This is likely the simplest encoder (small MLP or even linear projection).
