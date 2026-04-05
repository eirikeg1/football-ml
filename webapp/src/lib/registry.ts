import type { NodeDef } from "./types";

export const NODE_REGISTRY: NodeDef[] = [
  // Feature Extractors
  {
    id: "player_profile",
    label: "Player Profile Encoder",
    category: "feature_extractors",
    ports: [
      { name: "attributes", type: "input", dataType: "tensor" },
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
      { name: "form_sequence", type: "input", dataType: "tensor" },
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
      { name: "stats", type: "input", dataType: "tensor" },
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
      { name: "context", type: "input", dataType: "tensor" },
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
