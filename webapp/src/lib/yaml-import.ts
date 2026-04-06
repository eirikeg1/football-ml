import yaml from "js-yaml";
import {
  clearGraph,
  addNode,
  addConnection,
} from "./state.svelte";
import { NODE_REGISTRY } from "./registry";
import type { Category } from "./types";

// Layout constants for auto-placement by layer
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

interface YamlConfig {
  data_sources?: Record<string, Record<string, unknown>>;
  augmentation?: Record<string, Record<string, unknown>[] | Record<string, unknown>>;
  feature_extractors?: Record<string, Record<string, unknown>>;
  composition?: Record<string, Record<string, unknown>>;
  fusion?: Record<string, unknown>;
  temporal?: Record<string, unknown>;
  heads?: Record<string, Record<string, unknown>>;
}

export function importYaml(text: string): void {
  const config = yaml.load(text) as YamlConfig;
  if (!config) return;

  clearGraph();

  // Track created nodes by category for auto-connection
  const createdNodes: Record<string, { instanceId: string; defId: string }[]> =
    {};
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

    // Apply params from YAML
    for (const [key, val] of Object.entries(params)) {
      if (key === "type") continue; // type is used to select the module, not a param
      node.params[key] = val as number | string;
    }

    if (!createdNodes[category]) createdNodes[category] = [];
    createdNodes[category].push({ instanceId: node.instanceId, defId });

    return node.instanceId;
  }

  // Data sources
  if (config.data_sources) {
    for (const [key, params] of Object.entries(config.data_sources)) {
      placeNode(key, "data_sources", params);
    }
  }

  // Augmentation
  if (config.augmentation) {
    for (const [key, value] of Object.entries(config.augmentation)) {
      const items = Array.isArray(value) ? value : [value];
      for (const params of items) {
        placeNode(key, "augmentation", params);
      }
    }
  }

  // Feature extractors
  if (config.feature_extractors) {
    for (const [key, params] of Object.entries(config.feature_extractors)) {
      placeNode(key, "feature_extractors", params);
    }
  }

  // Composition
  if (config.composition) {
    for (const [key, params] of Object.entries(config.composition)) {
      placeNode(key, "composition", params);
    }
  }

  // Fusion
  if (config.fusion) {
    const fusionType = (config.fusion.type as string) || "transformer";
    const defId = `${fusionType}_fusion`;
    const params = { ...config.fusion };
    delete params.type;
    placeNode(defId, "fusion", params);
  }

  // Temporal
  if (config.temporal) {
    const temporalType = (config.temporal.type as string) || "gru";
    const defId = `${temporalType}_temporal`;
    const params = { ...config.temporal };
    delete params.type;
    placeNode(defId, "temporal", params);
  }

  // Heads
  if (config.heads) {
    for (const [key, params] of Object.entries(config.heads)) {
      placeNode(key, "heads", params);
    }
  }

  // Auto-connect layers in order
  const dataSources = createdNodes["data_sources"] || [];
  const augmentations = createdNodes["augmentation"] || [];
  const extractors = createdNodes["feature_extractors"] || [];
  const compositions = createdNodes["composition"] || [];
  const fusions = createdNodes["fusion"] || [];
  const temporals = createdNodes["temporal"] || [];
  const heads = createdNodes["heads"] || [];

  // Data sources → augmentation (if present), or → feature extractors
  const dataTargets = augmentations.length > 0 ? augmentations : extractors;
  for (const ds of dataSources) {
    const dsDef = NODE_REGISTRY.find((n) => n.id === ds.defId);
    const dsOutputPort = dsDef?.ports.find((p) => p.type === "output");
    if (!dsOutputPort) continue;
    for (const target of dataTargets) {
      const targetDef = NODE_REGISTRY.find((n) => n.id === target.defId);
      const inputPort = targetDef?.ports.find((p) => p.type === "input");
      if (inputPort) {
        addConnection(ds.instanceId, dsOutputPort.name, target.instanceId, inputPort.name);
      }
    }
  }

  // Augmentation → feature extractors
  if (augmentations.length > 0 && extractors.length > 0) {
    for (const aug of augmentations) {
      const augDef = NODE_REGISTRY.find((n) => n.id === aug.defId);
      const augOutput = augDef?.ports.find((p) => p.type === "output");
      if (!augOutput) continue;
      for (const ext of extractors) {
        const extDef = NODE_REGISTRY.find((n) => n.id === ext.defId);
        const inputPort = extDef?.ports.find((p) => p.type === "input");
        if (inputPort) {
          addConnection(aug.instanceId, augOutput.name, ext.instanceId, inputPort.name);
        }
      }
    }
  }

  // Feature extractors → composition (if present), or → fusion
  const nextLayer =
    compositions.length > 0 ? compositions : fusions;
  for (const ext of extractors) {
    for (const target of nextLayer) {
      const targetDef = NODE_REGISTRY.find((n) => n.id === target.defId);
      const inputPort = targetDef?.ports.find((p) => p.type === "input");
      if (inputPort) {
        addConnection(
          ext.instanceId,
          "embedding",
          target.instanceId,
          inputPort.name
        );
      }
    }
  }

  // Composition → fusion
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

  // Fusion → temporal
  for (const fus of fusions) {
    for (const temp of temporals) {
      addConnection(fus.instanceId, "match_repr", temp.instanceId, "sequence");
    }
  }

  // Temporal → heads
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
