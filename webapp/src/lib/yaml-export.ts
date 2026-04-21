import yaml from "js-yaml";
import type { NodeInstance, Connection } from "./types";
import type { TrainingConfig } from "./training-types";
import { getNodeDef } from "./registry";

interface YamlNode {
  type: string;
  position: [number, number];
  params: Record<string, unknown>;
  config?: Record<string, unknown>;
}

interface YamlConnection {
  from: string;
  to: string;
}

interface YamlGraph {
  nodes: Record<string, YamlNode>;
  connections: YamlConnection[];
}

export function exportYaml(
  nodes: NodeInstance[],
  connections: Connection[]
): string {
  // Build stable IDs: defId_1, defId_2, etc.
  const idCounters: Record<string, number> = {};
  const instanceToStable = new Map<string, string>();

  for (const node of nodes) {
    const count = (idCounters[node.defId] || 0) + 1;
    idCounters[node.defId] = count;
    const stableId = `${node.defId}_${count}`;
    instanceToStable.set(node.instanceId, stableId);
  }

  // Build nodes map
  const yamlNodes: Record<string, YamlNode> = {};
  for (const node of nodes) {
    const stableId = instanceToStable.get(node.instanceId)!;
    const yamlNode: YamlNode = {
      type: node.defId,
      position: [Math.round(node.x), Math.round(node.y)],
      params: { ...node.params },
    };
    if (
      node.detailConfig &&
      Object.keys(node.detailConfig).length > 0
    ) {
      yamlNode.config = node.detailConfig;
    }
    yamlNodes[stableId] = yamlNode;
  }

  // Build connections list
  const yamlConnections: YamlConnection[] = [];
  for (const conn of connections) {
    const fromStable = instanceToStable.get(conn.fromNode);
    const toStable = instanceToStable.get(conn.toNode);
    if (fromStable && toStable) {
      yamlConnections.push({
        from: `${fromStable}.${conn.fromPort}`,
        to: `${toStable}.${conn.toPort}`,
      });
    }
  }

  const graph: YamlGraph = {
    nodes: yamlNodes,
    connections: yamlConnections,
  };

  return yaml.dump(graph, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}

export function exportFullYaml(
  nodes: NodeInstance[],
  connections: Connection[],
  trainingConfig: TrainingConfig
): string {
  const pipelineYaml = exportYaml(nodes, connections);
  const pipeline = yaml.load(pipelineYaml) as Record<string, unknown>;
  const full = { ...pipeline, training: trainingConfig };
  return yaml.dump(full, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}
