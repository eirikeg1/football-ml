# Data Sources

## Currently Available

- **SofaScore API** (scraped): Basic match/player statistical data
- **ESPN API** (scraped): Basic match/player statistical data
- **Internet datasets**: Match results and related data

## Existing Resources to Integrate

### Elo / Club Elo
- Strong baseline for team strength
- Easy to compute or source from clubelo.com
- Use as a feature in TeamPerformanceEncoder
- Hard to beat for match outcome prediction alone — better to use as input than try to replace

### Expected Goals (xG)
- Well-studied, open-source implementations available
- Dual use: as a **feature** (feed xG/xGA into team performance) and potentially as a **pretrained component**
- Sources: available in some API data, or can be computed from shot-level data

### Football Manager Data
- Player attribute vectors (~30-50 attributes per player)
- Updated pre-season — snapshot nature means "update lag"
- Mitigated by combining with current season form data

## Recommended Additional Sources

### Transfermarkt
- Market values as proxy for squad/player quality
- Transfer history, contract data
- Squad depth information

### FBref / StatsBomb (open data)
- Advanced statistics (progressive passes, pressures, etc.)
- StatsBomb has a free open dataset for select competitions
- VAEP (Valuing Actions by Estimating Probabilities) from `socceraction` library — framework from KU Leuven for valuing on-ball actions, could feed into player form features

### Understat
- xG data for top European leagues
- Shot-level data with xG values

## Data Considerations

- Start with **one league** and get the pipeline working before expanding
- Ensure consistent player/team ID mapping across sources
- Handle missing data gracefully (not all sources cover all leagues/seasons)
