# Temporal Modeling

## Purpose

Capture dynamics over sequences of matches — how team/player performance evolves over time.

## Input

Sequence of match representations from the fusion layer:
```
Match t-N → Match t-N+1 → ... → Match t-1 → [predict Match t]
```

Each "Match" is the unified embedding produced by Layer 3 (fusion), which already incorporates player features, GNN team composition, and match context.

## Architecture Options

| Approach | Pros | Cons | Priority |
|---|---|---|---|
| **GRU** | Simple, proven, lightweight | Fixed hidden state | **First iteration** |
| LSTM | Slightly more expressive than GRU | More parameters, marginal gain | Later comparison |
| Temporal Transformer | Attention over full history, long-range | Data hungry, needs positional encoding | Later experiment |
| State-space (Mamba) | Efficient on long sequences | Newer, less ecosystem | Worth exploring |
| Exponential moving avg | No training, dead simple | Rigid decay, no learned dynamics | Baseline feature |

### Starting Point: GRU

The GRU hidden state becomes the "team form trajectory" — a learned representation of how the team has been performing over time.

## Temporal Considerations

### Variable Time Gaps
Matches aren't evenly spaced. Include as features:
- **Days since last match**: rest/fatigue
- **Days until next match**: rotation risk
- **Matches in last 7/14/30 days**: schedule congestion

### Competition Mixing
Teams play league, cup, and European matches in interleaved sequences. Options:
- Encode competition type as a feature and let the model learn to weight them
- Separate temporal streams per competition (more complex, explore later)

### Season Boundaries
Form doesn't fully carry over between seasons (squad changes, new manager). Options:
- Reset temporal state at season boundaries
- Dampen the hidden state (multiply by decay factor)
- Let the model learn this from the data (include "matchday in season" as feature)
