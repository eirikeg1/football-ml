import type { NodeDef } from "./types";

export const NODE_REGISTRY: NodeDef[] = [
  // Data Sources — Generic (implemented)
  {
    id: "sqlite_source",
    label: "SQLite Database",
    category: "data_sources",
    description:
      "Connect to a SQLite database. Select tables and columns in the detail panel. Auto-detects foreign key relationships.\n\nOutput: Multi-table dataset bundle.",
    ports: [{ name: "dataset", type: "output", dataType: "dataset" }],
    params: [{ name: "db_path", type: "string", default: "" }],
    detailPanel: "datasource_sqlite",
  },
  {
    id: "csv_source",
    label: "CSV Files",
    category: "data_sources",
    description:
      "Load CSV files from a directory. Each file becomes a table. Configure columns and relationships in the detail panel.\n\nOutput: Multi-table dataset bundle (one table per file).",
    ports: [{ name: "dataset", type: "output", dataType: "dataset" }],
    params: [{ name: "directory", type: "string", default: "" }],
    detailPanel: "datasource_csv",
  },
  {
    id: "table_selector",
    label: "Table Selector",
    category: "data_sources",
    description:
      "Select a single table from a multi-table dataset. Configure column filtering in the detail panel.\n\nInput: Multi-table dataset.\nOutput: Single table data.",
    ports: [
      { name: "dataset", type: "input", dataType: "dataset" },
      { name: "table_data", type: "output", dataType: "data" },
    ],
    params: [{ name: "table", type: "string", default: "" }],
    detailPanel: "table_selector",
  },
  {
    id: "materialization",
    label: "Materialize",
    category: "data_sources",
    description:
      "Convert a multi-table dataset into a single representation.\n\n- flatten: join all tables into one wide table\n- aligned: keep tables separate but aligned by key\n- graph: create a heterogeneous graph (PyTorch Geometric)\n\nInput: Multi-table dataset.\nOutput: Flat data or graph depending on strategy.",
    ports: [
      { name: "dataset", type: "input", dataType: "dataset" },
      { name: "output", type: "output", dataType: "data" },
      { name: "graph_output", type: "output", dataType: "graph" },
    ],
    params: [
      {
        name: "strategy",
        type: "select",
        default: "flatten",
        options: ["flatten", "aligned", "heterogeneous_graph"],
      },
    ],
    detailPanel: "materialization",
  },

  // Data Sources — Provider-specific (not yet implemented)
  {
    id: "sofascore_player_stats",
    label: "SofaScore Player Stats",
    category: "data_sources",
    description:
      "Per-match player statistics from SofaScore (ratings, goals, assists, passes, duels, etc.). Use as input for player-level feature extractors or augmentation.\n\nOutput: Tabular data with one row per player per match, columns for each stat.",
    ports: [{ name: "player_data", type: "output", dataType: "data" }],
    params: [
      {
        name: "format",
        type: "select",
        default: "sofascore_v1",
        options: ["sofascore_v1"],
      },
      { name: "features", type: "number", default: 25 },
    ],
    implemented: false,
  },
  {
    id: "sofascore_match_stats",
    label: "SofaScore Match Stats",
    category: "data_sources",
    description:
      "Team-level match statistics from SofaScore (possession, shots, corners, fouls, xG, etc.). Use as input for team performance encoders.\n\nOutput: Tabular data with one row per team per match.",
    ports: [{ name: "match_data", type: "output", dataType: "data" }],
    params: [
      {
        name: "format",
        type: "select",
        default: "sofascore_v1",
        options: ["sofascore_v1"],
      },
      { name: "features", type: "number", default: 30 },
    ],
    implemented: false,
  },
  {
    id: "espn_player_stats",
    label: "ESPN Player Stats",
    category: "data_sources",
    description:
      "Per-match player statistics from ESPN. Similar coverage to SofaScore but in ESPN's format. Can be merged with other player data sources.\n\nOutput: Tabular data with one row per player per match.",
    ports: [{ name: "player_data", type: "output", dataType: "data" }],
    params: [
      {
        name: "format",
        type: "select",
        default: "espn_v1",
        options: ["espn_v1"],
      },
      { name: "features", type: "number", default: 20 },
    ],
    implemented: false,
  },
  {
    id: "espn_match_stats",
    label: "ESPN Match Stats",
    category: "data_sources",
    description:
      "Team-level match statistics from ESPN. Use as input for team performance encoders or merge with other match data sources.\n\nOutput: Tabular data with one row per team per match.",
    ports: [{ name: "match_data", type: "output", dataType: "data" }],
    params: [
      {
        name: "format",
        type: "select",
        default: "espn_v1",
        options: ["espn_v1"],
      },
      { name: "features", type: "number", default: 18 },
    ],
    implemented: false,
  },
  {
    id: "fm_attributes",
    label: "FM Player Attributes",
    category: "data_sources",
    description:
      "Football Manager player attribute vectors (~50 attributes per player). Provides a pre-season snapshot of player quality and type. Note: FM data has an update lag since attributes are set pre-season. Combining with current season form data can compensate for this.\n\nOutput: Tabular data with one row per player, columns for each attribute (pace, passing, finishing, etc.).",
    ports: [{ name: "player_data", type: "output", dataType: "data" }],
    params: [
      {
        name: "format",
        type: "select",
        default: "fm_2025",
        options: ["fm_2024", "fm_2025"],
      },
      { name: "features", type: "number", default: 50 },
    ],
    implemented: false,
  },
  {
    id: "transfermarkt_values",
    label: "Transfermarkt Values",
    category: "data_sources",
    description:
      "Player market values, contract data, and transfer history from Transfermarkt. Market value serves as a proxy for player quality and squad depth.\n\nOutput: Tabular data with one row per player (value, age, contract end, position, etc.).",
    ports: [{ name: "player_data", type: "output", dataType: "data" }],
    params: [{ name: "features", type: "number", default: 8 }],
    implemented: false,
  },
  {
    id: "club_elo",
    label: "Club Elo Ratings",
    category: "data_sources",
    description:
      "Continuously updated Elo ratings for football clubs. A strong signal for team strength that can be fed into team-level encoders.\n\nOutput: Tabular data with one row per team per date (Elo rating, rank, rating change).",
    ports: [{ name: "team_data", type: "output", dataType: "data" }],
    params: [{ name: "features", type: "number", default: 3 }],
    implemented: false,
  },
  {
    id: "fbref_stats",
    label: "FBref Advanced Stats",
    category: "data_sources",
    description:
      "Advanced statistics from FBref (powered by StatsBomb). Includes progressive passes, pressures, shot-creating actions, xG, and more. Provides both player-level and match-level outputs.\n\nOutput (player_data): One row per player per match with advanced stats.\nOutput (match_data): One row per team per match with aggregate advanced stats.",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
      { name: "match_data", type: "output", dataType: "data" },
    ],
    params: [{ name: "features", type: "number", default: 40 }],
    implemented: false,
  },
  {
    id: "match_schedule",
    label: "Match Schedule",
    category: "data_sources",
    description:
      "Match schedule and fixture context: dates, competitions, venues, rest days between matches. Use for computing schedule density features (days since/until match, matches per week).\n\nOutput: Tabular data with one row per match (date, competition, home/away, venue, rest days).",
    ports: [{ name: "schedule_data", type: "output", dataType: "data" }],
    params: [{ name: "features", type: "number", default: 10 }],
    implemented: false,
  },
  {
    id: "custom_dataset",
    label: "Custom Dataset",
    category: "data_sources",
    description:
      "Load a custom dataset from a file path. Supports CSV, Parquet, and JSON formats. Use for any data source not covered by the built-in nodes.\n\nOutput: Tabular data loaded from the specified file.",
    ports: [{ name: "data", type: "output", dataType: "data" }],
    params: [
      { name: "path", type: "string", default: "" },
      {
        name: "format",
        type: "select",
        default: "csv",
        options: ["csv", "parquet", "json"],
      },
      { name: "features", type: "number", default: 10 },
    ],
    implemented: false,
  },

  // Augmentation / Preprocessing
  {
    id: "normalize",
    label: "Normalize",
    category: "augmentation",
    description:
      "Scale and normalize feature values. Place between data sources and feature extractors to ensure consistent value ranges.\n\n- standard: zero mean, unit variance (z-score)\n- minmax: scale to [0, 1]\n- robust: uses median and IQR, resilient to outliers\n\nInput: Raw tabular data.\nOutput: Normalized tabular data (same shape).",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      {
        name: "method",
        type: "select",
        default: "standard",
        options: ["standard", "minmax", "robust"],
      },
    ],
  },
  {
    id: "feature_selection",
    label: "Feature Selection",
    category: "augmentation",
    description:
      "Select a subset of input features to reduce dimensionality and remove noise.\n\n- all: pass through (no selection)\n- variance_threshold: drop low-variance features\n- mutual_info: rank by mutual information with target\n- manual: specify features explicitly\n\nInput: Tabular data.\nOutput: Tabular data with selected columns only.",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      {
        name: "method",
        type: "select",
        default: "all",
        options: ["all", "variance_threshold", "mutual_info", "manual"],
      },
      { name: "threshold", type: "number", default: 0.01 },
    ],
  },
  {
    id: "missing_value_imputation",
    label: "Missing Value Imputation",
    category: "augmentation",
    description:
      "Fill in missing values in the dataset. Important when merging sources with different coverage.\n\n- mean/median: replace with column mean or median\n- zero: fill with zeros\n- forward_fill: propagate last known value forward (useful for time series)\n\nInput: Tabular data with missing values.\nOutput: Tabular data with no missing values (same shape).",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      {
        name: "strategy",
        type: "select",
        default: "mean",
        options: ["mean", "median", "zero", "forward_fill"],
      },
    ],
  },
  {
    id: "temporal_window",
    label: "Temporal Window",
    category: "augmentation",
    description:
      "Create a sliding window over time-ordered data to capture recent history. Useful for building form features from per-match stats.\n\n- concat: stack the last N matches as one wide feature vector\n- mean: average over the window\n- ewma: exponentially weighted moving average (recent matches weighted more)\n\nInput: Time-ordered tabular data.\nOutput: Windowed features (one row per match, incorporating history).",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "window_size", type: "number", default: 5 },
      {
        name: "aggregation",
        type: "select",
        default: "concat",
        options: ["concat", "mean", "ewma"],
      },
    ],
  },
  {
    id: "noise_injection",
    label: "Noise Injection",
    category: "augmentation",
    description:
      "Add noise to training data for regularization and robustness. Only applied during training.\n\n- gaussian: add Gaussian noise scaled by the scale parameter\n- dropout: randomly zero out features\n- mixup: blend pairs of samples\n\nInput: Tabular data.\nOutput: Augmented tabular data (same shape, with noise added).",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      {
        name: "noise_type",
        type: "select",
        default: "gaussian",
        options: ["gaussian", "dropout", "mixup"],
      },
      { name: "scale", type: "number", default: 0.1 },
    ],
  },
  {
    id: "data_merge",
    label: "Data Merge",
    category: "augmentation",
    description:
      "Combine two data streams into one. Use to merge data from different sources (e.g., SofaScore + ESPN, or player stats + market values).\n\n- concat: concatenate columns side by side\n- left_join: keep all rows from input_a, match from input_b\n- inner_join: keep only rows that match in both inputs\n\nInput: Two tabular data streams.\nOutput: Merged tabular data.",
    ports: [
      { name: "input_a", type: "input", dataType: "data" },
      { name: "input_b", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      {
        name: "merge_on",
        type: "select",
        default: "player_id",
        options: ["player_id", "team_id", "match_id"],
      },
      {
        name: "method",
        type: "select",
        default: "concat",
        options: ["concat", "left_join", "inner_join"],
      },
    ],
  },
  {
    id: "rolling_stats",
    label: "Rolling Statistics",
    category: "augmentation",
    description:
      "Compute rolling statistics over a window of recent matches. Creates new features from the trend in each column.\n\n- mean: rolling average\n- mean_std: rolling mean and standard deviation\n- mean_std_minmax: mean, std, min, and max\n- all: mean, std, min, max, median, and trend\n\nInput: Time-ordered tabular data.\nOutput: Tabular data with rolling stat columns appended.",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "window", type: "number", default: 5 },
      {
        name: "stats",
        type: "select",
        default: "mean_std",
        options: ["mean", "mean_std", "mean_std_minmax", "all"],
      },
    ],
  },
  {
    id: "log_transform",
    label: "Log Transform",
    category: "augmentation",
    description:
      "Apply log(x + offset) to compress the range of skewed features. Useful for values like market value, attendance, or goal counts that span orders of magnitude.\n\nInput: Tabular data with positive-valued columns.\nOutput: Log-transformed tabular data (same shape).",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [{ name: "offset", type: "number", default: 1 }],
  },

  // Feature Extractors
  {
    id: "player_profile",
    label: "Player Profile Encoder",
    category: "feature_extractors",
    description:
      "Encode player attribute vectors (e.g., from Football Manager) into a dense embedding that captures player quality and type. Uses an MLP with configurable depth.\n\nCan be pretrained via multi-task learning (predict position + market value) to learn richer representations before plugging into the pipeline.\n\nInput: Player attribute vector (batch, input_dim).\nOutput: Player embedding (batch, output_dim).",
    ports: [
      { name: "attributes", type: "input", dataType: "data" },
      { name: "embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 50 },
      { name: "hidden_dim", type: "number", default: 128 },
      { name: "output_dim", type: "number", default: 64 },
      { name: "num_layers", type: "number", default: 3 },
    ],
  },
  {
    id: "player_form",
    label: "Player Form Encoder",
    category: "feature_extractors",
    description:
      "Encode a player's recent match statistics into a form embedding using a GRU over the last N matches. Captures current performance trajectory and momentum.\n\nInput: Sequence of per-match stat vectors (batch, seq_len, input_dim).\nOutput: Form embedding (batch, output_dim).",
    ports: [
      { name: "form_sequence", type: "input", dataType: "data" },
      { name: "embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 20 },
      { name: "hidden_dim", type: "number", default: 64 },
      { name: "output_dim", type: "number", default: 64 },
      { name: "seq_len", type: "number", default: 10 },
    ],
  },
  {
    id: "team_performance",
    label: "Team Performance Encoder",
    category: "feature_extractors",
    description:
      "Encode team-level performance statistics (xG, xGA, possession, points, Elo, etc.) into a team performance embedding.\n\nFeed with team stats from match data sources and Club Elo ratings.\n\nInput: Team stat vector (batch, input_dim).\nOutput: Team performance embedding (batch, output_dim).",
    ports: [
      { name: "stats", type: "input", dataType: "data" },
      { name: "embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 15 },
      { name: "hidden_dim", type: "number", default: 64 },
      { name: "output_dim", type: "number", default: 64 },
    ],
  },
  {
    id: "match_context",
    label: "Match Context Encoder",
    category: "feature_extractors",
    description:
      "Encode match context features: home/away, competition type, rest days, schedule density, derby flag, etc.\n\nFeed with data from the Match Schedule source. These are per-fixture features that don't change over the match.\n\nInput: Context feature vector (batch, input_dim).\nOutput: Context embedding (batch, output_dim).",
    ports: [
      { name: "context", type: "input", dataType: "data" },
      { name: "embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 10 },
      { name: "output_dim", type: "number", default: 32 },
    ],
  },

  // Composition
  {
    id: "lineup_gnn",
    label: "Lineup GNN",
    category: "composition",
    description:
      "Graph neural network over a match lineup. Players are nodes (with profile + form embeddings), edges represent positional/tactical relationships. Produces a team-level embedding via graph pooling.\n\nCaptures how well a specific combination of players works together, positional interactions, and overall lineup strength.\n\nInput: Player embeddings as graph node features (from Player Profile + Player Form encoders).\nOutput: Team embedding (batch, output_dim).",
    ports: [
      {
        name: "player_embeddings",
        type: "input",
        dataType: "embedding",
        multi: true,
      },
      { name: "team_embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "player_dim", type: "number", default: 128 },
      { name: "hidden_dim", type: "number", default: 128 },
      { name: "output_dim", type: "number", default: 64 },
      { name: "num_layers", type: "number", default: 2 },
    ],
  },

  {
    id: "hetero_gnn",
    label: "Heterogeneous GNN",
    category: "composition",
    description:
      "Heterogeneous Graph Transformer (HGT) over relational data tables. Tables become node types, FK relationships become edges. Learns entity representations through message passing across the full relational graph.\n\nTeams and competitions use learned embeddings. Match stats and events provide numeric features.\n\nProduces match representations by concatenating home + away team embeddings.\n\nInput: Multi-table dataset.\nOutput: Match embedding (2 x d_model dimensions).",
    ports: [
      { name: "dataset", type: "input", dataType: "dataset" },
      { name: "match_repr", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "d_model", type: "number", default: 128 },
      { name: "num_heads", type: "number", default: 8 },
      { name: "num_layers", type: "number", default: 3 },
      { name: "dropout", type: "number", default: 0.2 },
    ],
  },

  // Fusion
  {
    id: "transformer_fusion",
    label: "Transformer Fusion",
    category: "fusion",
    description:
      "Fuse multiple feature embeddings using a transformer encoder. Each input embedding becomes a token; self-attention learns cross-feature interactions (e.g., player form attending to opponent strength).\n\nHandles variable numbers of inputs — adding or removing upstream modules does not require changes to this node.\n\nInput: Multiple embedding vectors (one per connected upstream module).\nOutput: Unified match representation (batch, output_dim).",
    ports: [
      {
        name: "embeddings",
        type: "input",
        dataType: "embedding",
        multi: true,
      },
      { name: "match_repr", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "d_model", type: "number", default: 64 },
      { name: "nhead", type: "number", default: 4 },
      { name: "num_layers", type: "number", default: 2 },
      { name: "output_dim", type: "number", default: 128 },
    ],
  },
  {
    id: "hybrid_fusion",
    label: "Hybrid Fusion",
    category: "fusion",
    description:
      "Fuse multiple feature embeddings by first projecting and normalizing each input group independently, then combining them via a transformer encoder. Gives each feature group its own learned projection.\n\nWell suited when inputs have very different scales or semantics. Requires the number of inputs to be fixed at init time.\n\nInput: Multiple embedding vectors (fixed number of groups).\nOutput: Unified match representation (batch, output_dim).",
    ports: [
      {
        name: "embeddings",
        type: "input",
        dataType: "embedding",
        multi: true,
      },
      { name: "match_repr", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "d_model", type: "number", default: 64 },
      { name: "nhead", type: "number", default: 4 },
      { name: "num_layers", type: "number", default: 2 },
      { name: "output_dim", type: "number", default: 128 },
    ],
  },

  // Temporal
  {
    id: "gru_temporal",
    label: "GRU Temporal",
    category: "temporal",
    description:
      "GRU-based temporal model over a sequence of match representations. Captures form trajectory, momentum, and dynamics over time.\n\nProcesses the last N matches (each represented by the fusion output) and produces a temporal state summarizing recent history.\n\nInput: Sequence of match representations (batch, seq_len, input_dim).\nOutput: Temporal state (batch, output_dim).",
    ports: [
      { name: "sequence", type: "input", dataType: "embedding" },
      { name: "temporal_state", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 128 },
      { name: "hidden_dim", type: "number", default: 128 },
      { name: "output_dim", type: "number", default: 128 },
      { name: "num_layers", type: "number", default: 1 },
    ],
  },

  // Prediction Heads
  {
    id: "match_outcome",
    label: "Match Outcome",
    category: "heads",
    description:
      "Predict match outcome as win/draw/loss probabilities (3-class classification). The most common prediction target for football match prediction.\n\nInput: Temporal state (batch, input_dim).\nOutput: Logits for [win, draw, loss] (batch, 3). Apply softmax for probabilities.",
    ports: [
      { name: "temporal_state", type: "input", dataType: "embedding" },
      { name: "prediction", type: "output", dataType: "tensor" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 128 },
      { name: "num_classes", type: "number", default: 3 },
    ],
  },
  {
    id: "scoreline",
    label: "Scoreline",
    category: "heads",
    description:
      "Predict goal distributions for home and away teams. Outputs logits over discrete goal counts (0 to max_goals) for each team independently.\n\nInput: Temporal state (batch, input_dim).\nOutput: Goal distribution logits (batch, 2, max_goals+1) where dim 1 is [home, away].",
    ports: [
      { name: "temporal_state", type: "input", dataType: "embedding" },
      { name: "prediction", type: "output", dataType: "tensor" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 128 },
      { name: "max_goals", type: "number", default: 10 },
    ],
  },
  {
    id: "player_stat",
    label: "Player Stat",
    category: "heads",
    description:
      "Predict per-player statistics for an upcoming match (goals, assists, shots, key passes, etc.).\n\nInput: Temporal state (batch, input_dim).\nOutput: Predicted stats per player (batch, num_stats).",
    ports: [
      { name: "temporal_state", type: "input", dataType: "embedding" },
      { name: "prediction", type: "output", dataType: "tensor" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 128 },
      { name: "num_stats", type: "number", default: 5 },
    ],
  },
  {
    id: "match_stat",
    label: "Match Stat",
    category: "heads",
    description:
      "Predict team-level match statistics (possession %, total shots, xG, corners, fouls, etc.).\n\nInput: Temporal state (batch, input_dim).\nOutput: Predicted team stats (batch, num_stats).",
    ports: [
      { name: "temporal_state", type: "input", dataType: "embedding" },
      { name: "prediction", type: "output", dataType: "tensor" },
    ],
    params: [
      { name: "input_dim", type: "number", default: 128 },
      { name: "num_stats", type: "number", default: 8 },
    ],
  },
];

export function getNodeDef(id: string): NodeDef | undefined {
  return NODE_REGISTRY.find((n) => n.id === id);
}

export function getNodesByCategory(): Map<string, NodeDef[]> {
  const map = new Map<string, NodeDef[]>();
  for (const node of NODE_REGISTRY) {
    const list = map.get(node.category) || [];
    list.push(node);
    map.set(node.category, list);
  }
  return map;
}
