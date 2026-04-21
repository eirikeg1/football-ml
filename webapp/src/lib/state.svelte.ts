import type { NodeInstance, Connection, PendingConnection } from "./types";
import { getNodeDef } from "./registry";

let nextId = 1;

function generateId(): string {
  return `node_${nextId++}`;
}

function generateConnectionId(): string {
  return `conn_${nextId++}`;
}

export type OpenPopover =
  | { kind: "node-info"; nodeId: string }
  | { kind: "connection-issues"; connId: string };

// Reactive state using Svelte 5 runes
export const graphState = $state({
  nodes: [] as NodeInstance[],
  connections: [] as Connection[],
  selectedNodeIds: new Set<string>(),
  selectedConnectionId: null as string | null,
  pendingConnection: null as PendingConnection | null,
  openPopover: null as OpenPopover | null,
});

function samePopover(a: OpenPopover, b: OpenPopover): boolean {
  if (a.kind !== b.kind) return false;
  if (a.kind === "node-info" && b.kind === "node-info") return a.nodeId === b.nodeId;
  if (a.kind === "connection-issues" && b.kind === "connection-issues") return a.connId === b.connId;
  return false;
}

export function togglePopover(p: OpenPopover): void {
  if (graphState.openPopover && samePopover(graphState.openPopover, p)) {
    graphState.openPopover = null;
  } else {
    graphState.openPopover = p;
  }
}

export function closePopover(): void {
  graphState.openPopover = null;
}

export function addNode(
  defId: string,
  x: number,
  y: number
): NodeInstance | null {
  const def = getNodeDef(defId);
  if (!def) return null;

  const params: Record<string, number | string> = {};
  for (const p of def.params) {
    params[p.name] = p.default;
  }

  const node: NodeInstance = {
    instanceId: generateId(),
    defId,
    x,
    y,
    params,
  };

  graphState.nodes.push(node);
  return node;
}

export function removeNode(instanceId: string): void {
  graphState.connections = graphState.connections.filter(
    (c) => c.fromNode !== instanceId && c.toNode !== instanceId
  );
  graphState.nodes = graphState.nodes.filter(
    (n) => n.instanceId !== instanceId
  );
  graphState.selectedNodeIds.delete(instanceId);
}

export function removeSelectedNodes(): void {
  const ids = new Set(graphState.selectedNodeIds);
  graphState.connections = graphState.connections.filter(
    (c) => !ids.has(c.fromNode) && !ids.has(c.toNode)
  );
  graphState.nodes = graphState.nodes.filter(
    (n) => !ids.has(n.instanceId)
  );
  graphState.selectedNodeIds.clear();
}

export function moveNode(instanceId: string, x: number, y: number): void {
  const node = graphState.nodes.find((n) => n.instanceId === instanceId);
  if (node) {
    node.x = x;
    node.y = y;
  }
}

export function updateNodeParam(
  instanceId: string,
  paramName: string,
  value: number | string
): void {
  const node = graphState.nodes.find((n) => n.instanceId === instanceId);
  if (node) {
    node.params[paramName] = value;
  }
}

export function addConnection(
  fromNode: string,
  fromPort: string,
  toNode: string,
  toPort: string
): Connection | null {
  // Don't connect to self
  if (fromNode === toNode) return null;

  // Don't duplicate
  const exists = graphState.connections.some(
    (c) =>
      c.fromNode === fromNode &&
      c.fromPort === fromPort &&
      c.toNode === toNode &&
      c.toPort === toPort
  );
  if (exists) return null;

  // Incompatible connections (dtype, shape, dim, etc.) are still created — they
  // surface as red edges with a clickable error badge via the validation layer.
  // This is intentional: hiding the failed drop was worse UX than showing the bug.
  const toNodeInstance = graphState.nodes.find(
    (n) => n.instanceId === toNode
  );

  // Single-input ports replace any existing connection. Multi inputs allow unlimited.
  if (toNodeInstance) {
    const toDef = getNodeDef(toNodeInstance.defId);
    const portDef = toDef?.ports.find(
      (p) => p.name === toPort && p.type === "input"
    );
    if (portDef && !portDef.multi) {
      graphState.connections = graphState.connections.filter(
        (c) => !(c.toNode === toNode && c.toPort === toPort)
      );
    }
  }

  const conn: Connection = {
    id: generateConnectionId(),
    fromNode,
    fromPort,
    toNode,
    toPort,
  };

  graphState.connections.push(conn);
  return conn;
}

export function removeConnection(id: string): void {
  graphState.connections = graphState.connections.filter((c) => c.id !== id);
  if (graphState.selectedConnectionId === id) {
    graphState.selectedConnectionId = null;
  }
}

export function clearGraph(): void {
  graphState.nodes = [];
  graphState.connections = [];
  graphState.selectedNodeIds = new Set();
  graphState.selectedConnectionId = null;
  graphState.pendingConnection = null;
  graphState.openPopover = null;
  nextId = 1;
}

export function selectNode(instanceId: string | null, additive = false): void {
  graphState.selectedConnectionId = null;
  if (instanceId === null) {
    graphState.selectedNodeIds = new Set();
  } else if (additive) {
    const next = new Set(graphState.selectedNodeIds);
    if (next.has(instanceId)) {
      next.delete(instanceId);
    } else {
      next.add(instanceId);
    }
    graphState.selectedNodeIds = next;
  } else {
    graphState.selectedNodeIds = new Set([instanceId]);
  }
}

export function selectNodes(ids: string[]): void {
  graphState.selectedConnectionId = null;
  graphState.selectedNodeIds = new Set(ids);
}

export function selectConnection(id: string | null): void {
  graphState.selectedConnectionId = id;
  graphState.selectedNodeIds = new Set();
}

export function startConnection(
  fromNode: string,
  fromPort: string,
  fromX: number,
  fromY: number
): void {
  graphState.pendingConnection = {
    fromNode,
    fromPort,
    fromX,
    fromY,
    mouseX: fromX,
    mouseY: fromY,
  };
}

export function updatePendingConnection(mouseX: number, mouseY: number): void {
  if (graphState.pendingConnection) {
    graphState.pendingConnection.mouseX = mouseX;
    graphState.pendingConnection.mouseY = mouseY;
  }
}

export function finishConnection(toNode: string, toPort: string): void {
  if (graphState.pendingConnection) {
    addConnection(
      graphState.pendingConnection.fromNode,
      graphState.pendingConnection.fromPort,
      toNode,
      toPort
    );
    graphState.pendingConnection = null;
  }
}

export function cancelConnection(): void {
  graphState.pendingConnection = null;
}

export function updateDetailConfig(
  instanceId: string,
  config: Record<string, unknown>
): void {
  const node = graphState.nodes.find((n) => n.instanceId === instanceId);
  if (node) {
    node.detailConfig = config;
  }
}

export function getSelectedNode(): NodeInstance | null {
  if (graphState.selectedNodeIds.size !== 1) return null;
  const id = [...graphState.selectedNodeIds][0];
  return graphState.nodes.find((n) => n.instanceId === id) ?? null;
}
