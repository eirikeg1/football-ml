import yaml from "js-yaml";
import type { NodeInstance, Connection } from "./types";
import { getNodeDef } from "./registry";

interface YamlConfig {
  feature_extractors?: Record<string, Record<string, unknown>>;
  composition?: Record<string, Record<string, unknown>>;
  fusion?: Record<string, unknown>;
  temporal?: Record<string, unknown>;
  heads?: Record<string, Record<string, unknown>>;
}

export function exportYaml(
  nodes: NodeInstance[],
  connections: Connection[]
): string {
  const config: YamlConfig = {};

  for (const node of nodes) {
    const def = getNodeDef(node.defId);
    if (!def) continue;

    const params = { ...node.params };

    switch (def.category) {
      case "feature_extractors":
        if (!config.feature_extractors) config.feature_extractors = {};
        config.feature_extractors[def.id] = params;
        break;

      case "composition":
        if (!config.composition) config.composition = {};
        config.composition[def.id] = params;
        break;

      case "fusion":
        config.fusion = { type: def.id.replace("_fusion", ""), ...params };
        break;

      case "temporal":
        config.temporal = { type: def.id.replace("_temporal", ""), ...params };
        break;

      case "heads":
        if (!config.heads) config.heads = {};
        config.heads[def.id] = params;
        break;
    }
  }

  return yaml.dump(config, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}
