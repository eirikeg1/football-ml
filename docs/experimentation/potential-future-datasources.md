# Potential Future Data Sources

Data sources to evaluate and potentially integrate beyond the currently available SofaScore/ESPN scraped data and internet datasets.

## Team Strength / Ratings

### Club Elo (clubelo.com)
- Continuously updated Elo ratings for football clubs
- Strong baseline for team strength — hard to beat for match outcome prediction
- Use as a feature input rather than trying to replicate
- Free, easy to scrape or download

## Advanced Statistics

### FBref
- Advanced player and team statistics (progressive passes, pressures, shot-creating actions, etc.)
- Powered by StatsBomb data for top leagues
- Good coverage of major European leagues

### StatsBomb Open Data
- Free open dataset for select competitions (e.g., FA WSL, La Liga, select World Cups)
- Event-level data (passes, shots, carries, pressures)
- Can be used with the `socceraction` library for VAEP

### Understat
- xG data for top 5 European leagues
- Shot-level data with xG values per shot
- Useful for building or validating xG features

## Player Valuation / Squad Data

### Transfermarkt
- Market values as proxy for player/squad quality
- Transfer history and contract data
- Squad depth and age profiles
- Injury history

## Player Attributes

### Football Manager (already planned)
- ~30-50 attributes per player
- Updated pre-season (snapshot with lag)
- Useful for player type/quality profiling via learned embeddings

## Other

### Betting Odds (various providers)
- Market odds encode significant information about match probabilities
- Can serve as both a feature and an evaluation benchmark
- Sources: odds-portal, football-data.co.uk (historical odds)

### Weather Data
- Lower priority — marginal signal for most prediction tasks
- Could matter for specific stat predictions (e.g., passing accuracy)
- Available via open weather APIs matched to venue + kickoff time
