# Prediction Heads

## Purpose

Task-specific output layers that take the temporal state and produce predictions. Multiple heads can share the same upstream pipeline, enabling multi-task training and experimentation with different prediction targets.

## Planned Heads

### MatchOutcomeHead
- **Output**: W/D/L probabilities (3-class softmax)
- **Use case**: Match result prediction

### ScorelineHead
- **Output**: Goal distributions for each team (e.g., Poisson parameters or discrete distributions)
- **Use case**: Score prediction, derived probabilities

### PlayerStatHead
- **Output**: Predicted statistics for individual players (goals, assists, shots, etc.)
- **Use case**: Player performance prediction
- **Note**: May need player-level temporal state in addition to team-level

### MatchStatHead
- **Output**: Team-level statistics (possession, shots, xG, corners, etc.)
- **Use case**: Match statistics prediction

## Design Notes

- All heads receive the same temporal state vector as input
- Heads are independently swappable — train with one head, add others later
- Can train multiple heads simultaneously (multi-task) or individually
- The project is experimentation-focused: prediction targets may expand over time to include match events, probabilities of specific occurrences, etc.
