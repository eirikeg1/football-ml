# Feature Taxonomy

Features are organized by **granularity and volatility** — what level they describe and how often they change.

## Feature Categories

| Category | Granularity | Update Frequency | Examples |
|---|---|---|---|
| **Player Profile** | Player | Seasonal (slow) | FM attributes, position, market value, age |
| **Player Form** | Player | Per-match (fast) | Goals, assists, minutes, ratings over recent matches |
| **Team Composition** | Team/Match | Per-match | Lineup, formation, GNN-derived embeddings |
| **Team Performance** | Team | Per-match | xG, possession, points, win streaks, Elo rating |
| **Match Context** | Match | Per-match (static per fixture) | Home/away, competition, rest days, derby, weather |
| **Opponent-Relative** | Match | Per-match (derived) | Elo difference, head-to-head, style matchup |

## Why This Taxonomy

Each category maps to a **feature module** in the pipeline. This means:
- Adding a new player-level feature just requires updating the relevant player encoder
- Adding a new category (e.g., tactical features) means adding a new encoder module
- The fusion layer handles any combination of active feature groups

## Temporal Features

Time-related features are embedded within Match Context but are worth calling out:

- **Days since last match**: rest/fatigue indicator
- **Days until next match**: rotation risk indicator
- **Matches in last N days**: captures schedule congestion better than single gap
- **Competition importance weighting**: teams may rotate squads before important upcoming fixtures (e.g., Champions League knockout)
