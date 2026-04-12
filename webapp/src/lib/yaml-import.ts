import yaml from "js-yaml";
import { clearGraph, addNode, addConnection } from "./state.svelte";
import { NODE_REGISTRY } from "./registry";
import type { Category } from "./types";

// ── Graph-native format ─────────────────────────────────────────────

interface YamlNode {
  type: string;
  position?: [number, number];
  params?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

interface YamlConnection {
  from: string;
  to: string;
}

interface YamlGraph {
  nodes: Record<string, YamlNode>;
  connections?: YamlConnection[];
}

// Auto-layout: position nodes by category column, stacked vertically
function autoPosition(defId: string, categoryCounts: Record<string, number>): [number, number] {
  const def = NODE_REGISTRY.find((n) => n.id === defId);
  const category = def?.category ?? "feature_extractors";
  const col = LAYER_X[category] ?? 650;
  const count = categoryCounts[category] || 0;
  categoryCounts[category] = count + 1;
  return [col, START_Y + count * NODE_SPACING_Y];
}

function importGraphFormat(graph: YamlGraph): void {
  clearGraph();

  const stableToInstance = new Map<string, string>();
  const categoryCounts: Record<string, number> = {};

  for (const [stableId, yamlNode] of Object.entries(graph.nodes)) {
    const [x, y] = yamlNode.position ?? autoPosition(yamlNode.type, categoryCounts);
    const node = addNode(yamlNode.type, x, y);
    if (!node) continue;

    for (const [key, val] of Object.entries(yamlNode.params ?? {})) {
      node.params[key] = val as number | string;
    }

    if (yamlNode.config && Object.keys(yamlNode.config).length > 0) {
      node.detailConfig = yamlNode.config;
    }

    stableToInstance.set(stableId, node.instanceId);
  }

  for (const conn of graph.connections ?? []) {
    const [fromId, fromPort] = splitRef(conn.from);
    const [toId, toPort] = splitRef(conn.to);
    const fromInstance = stableToInstance.get(fromId);
    const toInstance = stableToInstance.get(toId);
    if (fromInstance && toInstance && fromPort && toPort) {
      addConnection(fromInstance, fromPort, toInstance, toPort);
    }
  }
}

function splitRef(ref: string): [string, string] {
  const dot = ref.lastIndexOf(".");
  if (dot === -1) return [ref, ""];
  return [ref.slice(0, dot), ref.slice(dot + 1)];
}

// ── Legacy pipeline config format (backwards compat) ────────────────

interface LegacyConfig {
  data_sources?: Record<string, Record<string, unknown>>;
  augmentation?: Record<
    string,
    Record<string, unknown>[] | Record<string, unknown>
  >;
  feature_extractors?: Record<string, Record<string, unknown>>;
  composition?: Record<string, Record<string, unknown>>;
  fusion?: Record<string, unknown>;
  temporal?: Record<string, unknown>;
  heads?: Record<string, Record<string, unknown>>;
}

const LAYER_X: Record<Category, number> = {
  data_sources: 50,
  augmentation: 350,
  feature_extractors: 650,
  composition: 950,
  fusion: 1250,
  temporal: 1550,
  heads: 1850,
};

const START_Y = 50;
const NODE_SPACING_Y = 200;

function importLegacyFormat(config: LegacyConfig): void {
  clearGraph();

  const createdNodes: Record<
    string,
    { instanceId: string; defId: string }[]
  > = {};
  const layerCounts: Record<string, number> = {};

  function placeNode(
    defId: string,
    category: Category,
    params: Record<string, unknown>
  ): string | null {
    const count = layerCounts[category] || 0;
    layerCounts[category] = count + 1;

    const x = LAYER_X[category];
    const y = START_Y + count * NODE_SPACING_Y;

    const node = addNode(defId, x, y);
    if (!node) return null;

    for (const [key, val] of Object.entries(params)) {
      if (key === "type") continue;
      node.params[key] = val as number | string;
    }

    if (!createdNodes[category]) createdNodes[category] = [];
    createdNodes[category].push({ instanceId: node.instanceId, defId });
    return node.instanceId;
  }

  if (config.data_sources) {
    for (const [key, params] of Object.entries(config.data_sources)) {
      placeNode(key, "data_sources", params);
    }
  }

  if (config.augmentation) {
    for (const [key, value] of Object.entries(config.augmentation)) {
      const items = Array.isArray(value) ? value : [value];
      for (const params of items) {
        placeNode(key, "augmentation", params);
      }
    }
  }

  if (config.feature_extractors) {
    for (const [key, params] of Object.entries(config.feature_extractors)) {
      placeNode(key, "feature_extractors", params);
    }
  }

  if (config.composition) {
    for (const [key, params] of Object.entries(config.composition)) {
      placeNode(key, "composition", params);
    }
  }

  if (config.fusion) {
    const fusionType = (config.fusion.type as string) || "transformer";
    const defId = `${fusionType}_fusion`;
    const params = { ...config.fusion };
    delete params.type;
    placeNode(defId, "fusion", params);
  }

  if (config.temporal) {
    const temporalType = (config.temporal.type as string) || "gru";
    const defId = `${temporalType}_temporal`;
    const params = { ...config.temporal };
    delete params.type;
    placeNode(defId, "temporal", params);
  }

  if (config.heads) {
    for (const [key, params] of Object.entries(config.heads)) {
      placeNode(key, "heads", params);
    }
  }

  // Heuristic auto-connect for legacy format
  const dataSources = createdNodes["data_sources"] || [];
  const augmentations = createdNodes["augmentation"] || [];
  const extractors = createdNodes["feature_extractors"] || [];
  const compositions = createdNodes["composition"] || [];
  const fusions = createdNodes["fusion"] || [];
  const temporals = createdNodes["temporal"] || [];
  const heads = createdNodes["heads"] || [];

  const dataTargets = augmentations.length > 0 ? augmentations : extractors;
  for (const ds of dataSources) {
    const dsDef = NODE_REGISTRY.find((n) => n.id === ds.defId);
    const dsOut = dsDef?.ports.find((p) => p.type === "output");
    if (!dsOut) continue;
    for (const target of dataTargets) {
      const tDef = NODE_REGISTRY.find((n) => n.id === target.defId);
      const tIn = tDef?.ports.find((p) => p.type === "input");
      if (tIn)
        addConnection(ds.instanceId, dsOut.name, target.instanceId, tIn.name);
    }
  }

  if (augmentations.length > 0 && extractors.length > 0) {
    for (const aug of augmentations) {
      const aDef = NODE_REGISTRY.find((n) => n.id === aug.defId);
      const aOut = aDef?.ports.find((p) => p.type === "output");
      if (!aOut) continue;
      for (const ext of extractors) {
        const eDef = NODE_REGISTRY.find((n) => n.id === ext.defId);
        const eIn = eDef?.ports.find((p) => p.type === "input");
        if (eIn)
          addConnection(
            aug.instanceId,
            aOut.name,
            ext.instanceId,
            eIn.name
          );
      }
    }
  }

  const nextLayer = compositions.length > 0 ? compositions : fusions;
  for (const ext of extractors) {
    for (const target of nextLayer) {
      const tDef = NODE_REGISTRY.find((n) => n.id === target.defId);
      const tIn = tDef?.ports.find((p) => p.type === "input");
      if (tIn)
        addConnection(ext.instanceId, "embedding", target.instanceId, tIn.name);
    }
  }

  if (compositions.length > 0 && fusions.length > 0) {
    for (const comp of compositions) {
      for (const fus of fusions) {
        addConnection(
          comp.instanceId,
          "team_embedding",
          fus.instanceId,
          "embeddings"
        );
      }
    }
  }

  for (const fus of fusions) {
    for (const temp of temporals) {
      addConnection(fus.instanceId, "match_repr", temp.instanceId, "sequence");
    }
  }

  for (const temp of temporals) {
    for (const head of heads) {
      addConnection(
        temp.instanceId,
        "temporal_state",
        head.instanceId,
        "temporal_state"
      );
    }
  }
}

// ── Entry point ─────────────────────────────────────────────────────

export function importYaml(text: string): void {
  const data = yaml.load(text) as Record<string, unknown>;
  if (!data) return;

  // Detect format: graph-native has a "nodes" key with objects that have "type"
  if (data.nodes && typeof data.nodes === "object" && !Array.isArray(data.nodes)) {
    const firstNode = Object.values(data.nodes)[0] as Record<string, unknown> | undefined;
    if (firstNode && "type" in firstNode) {
      importGraphFormat(data as unknown as YamlGraph);
      return;
    }
  }

  // Fallback: legacy pipeline config format
  importLegacyFormat(data as unknown as LegacyConfig);
}
