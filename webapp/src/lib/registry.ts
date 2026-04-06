import type { NodeDef } from "./types";

export const NODE_REGISTRY: NodeDef[] = [
  // Data Sources
  {
    id: "sofascore_player_stats",
    label: "SofaScore Player Stats",
    category: "data_sources",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "format", type: "select", default: "sofascore_v1", options: ["sofascore_v1"] },
      { name: "features", type: "number", default: 25 },
    ],
  },
  {
    id: "sofascore_match_stats",
    label: "SofaScore Match Stats",
    category: "data_sources",
    ports: [
      { name: "match_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "format", type: "select", default: "sofascore_v1", options: ["sofascore_v1"] },
      { name: "features", type: "number", default: 30 },
    ],
  },
  {
    id: "espn_player_stats",
    label: "ESPN Player Stats",
    category: "data_sources",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "format", type: "select", default: "espn_v1", options: ["espn_v1"] },
      { name: "features", type: "number", default: 20 },
    ],
  },
  {
    id: "espn_match_stats",
    label: "ESPN Match Stats",
    category: "data_sources",
    ports: [
      { name: "match_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "format", type: "select", default: "espn_v1", options: ["espn_v1"] },
      { name: "features", type: "number", default: 18 },
    ],
  },
  {
    id: "fm_attributes",
    label: "FM Player Attributes",
    category: "data_sources",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "format", type: "select", default: "fm_2025", options: ["fm_2024", "fm_2025"] },
      { name: "features", type: "number", default: 50 },
    ],
  },
  {
    id: "transfermarkt_values",
    label: "Transfermarkt Values",
    category: "data_sources",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "features", type: "number", default: 8 },
    ],
  },
  {
    id: "club_elo",
    label: "Club Elo Ratings",
    category: "data_sources",
    ports: [
      { name: "team_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "features", type: "number", default: 3 },
    ],
  },
  {
    id: "fbref_stats",
    label: "FBref Advanced Stats",
    category: "data_sources",
    ports: [
      { name: "player_data", type: "output", dataType: "data" },
      { name: "match_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "features", type: "number", default: 40 },
    ],
  },
  {
    id: "match_schedule",
    label: "Match Schedule",
    category: "data_sources",
    ports: [
      { name: "schedule_data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "features", type: "number", default: 10 },
    ],
  },
  {
    id: "custom_dataset",
    label: "Custom Dataset",
    category: "data_sources",
    ports: [
      { name: "data", type: "output", dataType: "data" },
    ],
    params: [
      { name: "path", type: "string", default: "" },
      { name: "format", type: "select", default: "csv", options: ["csv", "parquet", "json"] },
      { name: "features", type: "number", default: 10 },
    ],
  },

  // Augmentation / Preprocessing
  {
    id: "normalize",
    label: "Normalize",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "method", type: "select", default: "standard", options: ["standard", "minmax", "robust"] },
    ],
  },
  {
    id: "feature_selection",
    label: "Feature Selection",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "method", type: "select", default: "all", options: ["all", "variance_threshold", "mutual_info", "manual"] },
      { name: "threshold", type: "number", default: 0.01 },
    ],
  },
  {
    id: "missing_value_imputation",
    label: "Missing Value Imputation",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "strategy", type: "select", default: "mean", options: ["mean", "median", "zero", "forward_fill"] },
    ],
  },
  {
    id: "temporal_window",
    label: "Temporal Window",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "window_size", type: "number", default: 5 },
      { name: "aggregation", type: "select", default: "concat", options: ["concat", "mean", "ewma"] },
    ],
  },
  {
    id: "noise_injection",
    label: "Noise Injection",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "noise_type", type: "select", default: "gaussian", options: ["gaussian", "dropout", "mixup"] },
      { name: "scale", type: "number", default: 0.1 },
    ],
  },
  {
    id: "data_merge",
    label: "Data Merge",
    category: "augmentation",
    ports: [
      { name: "input_a", type: "input", dataType: "data" },
      { name: "input_b", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "merge_on", type: "select", default: "player_id", options: ["player_id", "team_id", "match_id"] },
      { name: "method", type: "select", default: "concat", options: ["concat", "left_join", "inner_join"] },
    ],
  },
  {
    id: "rolling_stats",
    label: "Rolling Statistics",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "window", type: "number", default: 5 },
      { name: "stats", type: "select", default: "mean_std", options: ["mean", "mean_std", "mean_std_minmax", "all"] },
    ],
  },
  {
    id: "log_transform",
    label: "Log Transform",
    category: "augmentation",
    ports: [
      { name: "input", type: "input", dataType: "data" },
      { name: "output", type: "output", dataType: "data" },
    ],
    params: [
      { name: "offset", type: "number", default: 1 },
    ],
  },

  // Feature Extractors
  {
    id: "player_profile",
    label: "Player Profile Encoder",
    category: "feature_extractors",
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
    ports: [
      { name: "player_embeddings", type: "input", dataType: "embedding", multi: true },
      { name: "team_embedding", type: "output", dataType: "embedding" },
    ],
    params: [
      { name: "player_dim", type: "number", default: 128 },
      { name: "hidden_dim", type: "number", default: 128 },
      { name: "output_dim", type: "number", default: 64 },
      { name: "num_layers", type: "number", default: 2 },
    ],
  },

  // Fusion
  {
    id: "transformer_fusion",
    label: "Transformer Fusion",
    category: "fusion",
    ports: [
      { name: "embeddings", type: "input", dataType: "embedding", multi: true },
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
    ports: [
      { name: "embeddings", type: "input", dataType: "embedding", multi: true },
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
