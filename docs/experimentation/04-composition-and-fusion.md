# Composition and Fusion Layers

## Layer 2: Lineup GNN (Composition)

**Purpose**: Combine individual player embeddings with formation/positional structure to produce a team-level representation for a specific match lineup.

**Framework**: PyTorch Geometric

### Graph Structure
- **Nodes**: Players in the lineup (11 per team), each with their combined profile + form embedding
- **Edges**: Positional/tactical relationships (adjacent positions, passing lanes, etc.)
- **Output**: Team-level embedding via graph pooling

### What It Captures
- How well this specific combination of players works together
- Positional interactions (e.g., how well does this midfield pairing complement each other)
- Overall team strength based on the actual lineup (not just squad quality)
- Similarity to lineups the team has fielded before, and how those performed against similar opposition profiles

## Layer 3: Fusion (Cross-Feature Interaction)

**Purpose**: Aggregate all feature embeddings into a unified match representation before temporal modeling.

### Options Considered

#### Option A: Simple Concatenation + Projection
```
[player_emb | team_emb | context_emb | gnn_emb] → Linear → match_vector
```
- **Pros**: Simple, fast, easy to debug
- **Cons**: No cross-feature interaction — temporal model must learn both feature interactions AND temporal dynamics

#### Option B: Transformer Encoder (selected for first iteration)
```
[player_emb, team_emb, context_emb, gnn_emb] → TransformerEncoder → match_vector
```
Each feature group becomes a "token." Self-attention lets features attend to each other.

- **Pros**: Handles variable number of input tokens (modularity-friendly), learns which features are relevant to each other, clean separation of concerns
- **Cons**: Slightly more complex than concatenation
- **Config**: 2-3 encoder layers, 4-8 attention heads (attending over ~5-10 tokens, not thousands)

#### Option C: Hybrid (project + pool within groups, then transformer)
```
player features → player_emb  ─┐
team features   → team_emb    ─┤→ TransformerEncoder → match_vector
context features → ctx_emb    ─┘
```

### Decision
Implement modules for both B and C, but wire up **Option B** in the initial pipeline. Option A can be tested later as a simpler baseline.

### Why Transformer Encoder for Fusion
- **Modularity**: Adding/removing feature modules just changes the number of input tokens — nothing downstream breaks
- **Feature interaction**: Whether a team's recent form is "good" depends on who they played against. The fusion layer can capture this.
- **Separation of concerns**: Fusion handles "what does this match look like," temporal model handles "how has this been changing"
