import type {
  Connection,
  NodeInstance,
  PortDef,
  PortShape,
  ValidationIssue,
  ValidationSeverity,
} from "./types";
import { findShapeAdapters, getNodeDef, NODE_REGISTRY } from "./registry";

type PortType = "input" | "output";

export interface GraphSlice {
  nodes: NodeInstance[];
  connections: Connection[];
}

export interface PortRequirementStatus {
  portName: string;
  portLabel: string;
  dataType: string;
  shape: PortShape;
  widthParam?: string;
  expectedWidth?: number; // resolved from params
  required: boolean;
  multi: boolean;
  multiSemantics?: "concat" | "stack";
  connections: {
    connId: string;
    fromNodeId: string;
    fromNodeLabel: string;
    fromPort: string;
    actualShape?: PortShape;
    actualWidth?: number;
    issues: ValidationIssue[];
  }[];
  status: "ok" | "missing" | "warning" | "error";
  issues: ValidationIssue[]; // port-level issues (e.g., required_input_missing, aggregated)
}

export interface OutputConsumer {
  connId: string;
  toNodeId: string;
  toNodeLabel: string;
  toPort: string;
  expectedShape?: PortShape;
  expectedWidth?: number;
  issues: ValidationIssue[];
}

export interface OutputPortStatus {
  portName: string;
  dataType: string;
  shape: PortShape;
  widthParam?: string;
  width?: number;
  consumers: OutputConsumer[];
  status: "ok" | "warning" | "error";
}

export interface NodeValidationReport {
  inputs: PortRequirementStatus[];
  outputs: OutputPortStatus[];
  worstSeverity: "ok" | "warning" | "error";
}

// --- helpers ---

function portOf(
  node: NodeInstance,
  portName: string,
  portType: PortType
): PortDef | undefined {
  const def = getNodeDef(node.defId);
  return def?.ports.find((p) => p.name === portName && p.type === portType);
}

function nodeById(state: GraphSlice, id: string): NodeInstance | undefined {
  return state.nodes.find((n) => n.instanceId === id);
}

function nodeLabel(node: NodeInstance | undefined): string {
  if (!node) return "?";
  return getNodeDef(node.defId)?.label ?? node.defId;
}

function effectiveShape(port: PortDef): PortShape {
  if (port.shape) return port.shape;
  if (port.dataType === "dataset") return "dataset";
  if (port.dataType === "graph") return "graph";
  return "flat";
}

function resolveWidth(
  port: PortDef,
  node: NodeInstance
): number | undefined {
  if (!port.widthParam) return undefined;
  const raw = node.params[port.widthParam];
  if (raw === undefined || raw === null || raw === "") return undefined;
  const n = typeof raw === "number" ? raw : parseFloat(String(raw));
  if (!isFinite(n)) return undefined;
  return n;
}

function shapeLabel(s: PortShape): string {
  return s;
}

// --- cycle detection ---

export function wouldCreateCycle(
  fromNodeId: string,
  toNodeId: string,
  state: GraphSlice
): boolean {
  // If there's already a path from toNode back to fromNode, adding from→to creates a cycle.
  if (fromNodeId === toNodeId) return true;
  const adj = new Map<string, string[]>();
  for (const c of state.connections) {
    const list = adj.get(c.fromNode) ?? [];
    list.push(c.toNode);
    adj.set(c.fromNode, list);
  }
  // Also include the candidate edge.
  const list = adj.get(fromNodeId) ?? [];
  list.push(toNodeId);
  adj.set(fromNodeId, list);

  // DFS from toNodeId; if we hit fromNodeId we have a cycle.
  const stack = [toNodeId];
  const visited = new Set<string>();
  while (stack.length > 0) {
    const cur = stack.pop()!;
    if (cur === fromNodeId) return true;
    if (visited.has(cur)) continue;
    visited.add(cur);
    const next = adj.get(cur);
    if (next) stack.push(...next);
  }
  return false;
}

function connectionInCycle(conn: Connection, state: GraphSlice): boolean {
  // A connection participates in a cycle if there's a path from conn.toNode back to conn.fromNode
  // using the current connection set. We walk forward from toNode; if we reach fromNode we have a cycle.
  const adj = new Map<string, string[]>();
  for (const c of state.connections) {
    const list = adj.get(c.fromNode) ?? [];
    list.push(c.toNode);
    adj.set(c.fromNode, list);
  }
  const stack = [conn.toNode];
  const visited = new Set<string>();
  while (stack.length > 0) {
    const cur = stack.pop()!;
    if (cur === conn.fromNode) return true;
    if (visited.has(cur)) continue;
    visited.add(cur);
    const next = adj.get(cur);
    if (next) stack.push(...next);
  }
  return false;
}

// --- per-connection checks ---

export function validateConnection(
  conn: Connection,
  state: GraphSlice
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  const fromNode = nodeById(state, conn.fromNode);
  const toNode = nodeById(state, conn.toNode);
  if (!fromNode || !toNode) return issues;

  const fromDef = getNodeDef(fromNode.defId);
  const toDef = getNodeDef(toNode.defId);
  if (!fromDef || !toDef) return issues;

  const fromPort = portOf(fromNode, conn.fromPort, "output");
  const toPort = portOf(toNode, conn.toPort, "input");
  if (!fromPort || !toPort) return issues;

  // 1. dtype mismatch
  if (fromPort.dataType !== toPort.dataType) {
    issues.push({
      severity: "error",
      code: "dtype_mismatch",
      message: `Type mismatch: ${fromPort.dataType} → ${toPort.dataType}`,
      detail: `Upstream "${fromDef.label}.${fromPort.name}" produces ${fromPort.dataType} but "${toDef.label}.${toPort.name}" expects ${toPort.dataType}. These are incompatible.`,
    });
  }

  // 2. shape mismatch
  const fromShape = effectiveShape(fromPort);
  const toShape = effectiveShape(toPort);
  if (fromShape !== toShape) {
    // Look for registry nodes that can bridge this shape gap for the same
    // dataType (embedding, data, etc.), so we can name concrete remediation
    // nodes in the detail instead of a generic phrasing.
    const adapters =
      fromPort.dataType === toPort.dataType
        ? findShapeAdapters(fromShape, toShape, fromPort.dataType)
        : [];
    const adapterHint =
      adapters.length > 0
        ? ` Insert ${adapters.length === 1 ? "a" : "one of"} ${adapters
            .map((a) => `"${a.label}"`)
            .join(" or ")} between them to convert ${shapeLabel(fromShape)} → ${shapeLabel(toShape)}.`
        : " Insert an adapter node (or change the upstream source) to match the expected shape.";
    issues.push({
      severity: "error",
      code: "shape_mismatch",
      message: `Shape mismatch: ${shapeLabel(fromShape)} → ${shapeLabel(toShape)}`,
      detail: `Upstream "${fromDef.label}" produces a ${shapeLabel(fromShape)} output but "${toDef.label}" expects ${shapeLabel(toShape)}.${adapterHint}`,
    });
  }

  // 3. dim mismatch — only valid to check when BOTH sides declare a width param
  //    and the downstream port is not a multi input (multi inputs get aggregate checks below).
  const fromWidth = resolveWidth(fromPort, fromNode);
  const toWidth = resolveWidth(toPort, toNode);
  const downstreamIsMulti = !!toPort.multi;

  if (fromPort.widthParam && toPort.widthParam && !downstreamIsMulti) {
    if (fromWidth === undefined || toWidth === undefined) {
      issues.push({
        severity: "warning",
        code: "upstream_unset",
        message: "Width not set — can't verify dim match",
        detail: `Set "${fromPort.widthParam}" on "${fromDef.label}" and "${toPort.widthParam}" on "${toDef.label}" so the feature dimension can be verified.`,
      });
    } else if (fromWidth !== toWidth) {
      issues.push({
        severity: "error",
        code: "dim_mismatch",
        message: `Dim mismatch: ${fromWidth} → ${toWidth}`,
        detail: `Upstream "${fromDef.label}" outputs width ${fromWidth} (${fromPort.widthParam}) but downstream "${toDef.label}" expects width ${toWidth} (${toPort.widthParam}).`,
      });
    }
  }

  // 4. multi-input aggregate check — emit on every edge into this port so the bad edges are visible
  if (downstreamIsMulti && toPort.widthParam) {
    const semantics = toPort.multiSemantics ?? "concat";
    const incoming = state.connections.filter(
      (c) => c.toNode === conn.toNode && c.toPort === conn.toPort
    );
    const widths = incoming.map((c) => {
      const n = nodeById(state, c.fromNode);
      const p = n ? portOf(n, c.fromPort, "output") : undefined;
      return n && p ? resolveWidth(p, n) : undefined;
    });
    const allKnown = widths.every((w) => w !== undefined);
    if (allKnown && toWidth !== undefined) {
      if (semantics === "stack") {
        const first = widths[0];
        const uniform = widths.every((w) => w === first);
        if (!uniform || first !== toWidth) {
          issues.push({
            severity: "error",
            code: "multi_stack_mismatch",
            message: `Stack fusion requires equal widths of ${toWidth}`,
            detail: `"${toDef.label}" combines its inputs by stacking into tokens, so every upstream width must equal ${toWidth} (${toPort.widthParam}). Current upstream widths: [${widths.join(", ")}].`,
          });
        }
      } else if (semantics === "concat") {
        const sum = widths.reduce<number>((s, w) => s + (w ?? 0), 0);
        if (sum !== toWidth) {
          issues.push({
            severity: "error",
            code: "multi_sum_mismatch",
            message: `Concat width ${sum} ≠ expected ${toWidth}`,
            detail: `"${toDef.label}" concatenates its inputs, so the sum of upstream widths must equal ${toWidth} (${toPort.widthParam}). Current sum: ${sum} from [${widths.join(", ")}].`,
          });
        }
      }
    }
  }

  // 5. cycle
  if (connectionInCycle(conn, state)) {
    issues.push({
      severity: "error",
      code: "cycle",
      message: "This connection forms a cycle",
      detail: `Following connections forward from "${toDef.label}" eventually leads back to "${fromDef.label}". Pipelines must be acyclic.`,
    });
  }

  // 6. not implemented (warning)
  if (fromDef.implemented === false || toDef.implemented === false) {
    const which =
      fromDef.implemented === false && toDef.implemented === false
        ? "both endpoints"
        : fromDef.implemented === false
          ? `"${fromDef.label}"`
          : `"${toDef.label}"`;
    issues.push({
      severity: "warning",
      code: "not_implemented",
      message: `${which} not yet implemented`,
      detail: `This connection is fine to wire up, but ${which} still needs implementation before the pipeline will run.`,
    });
  }

  // 7. category hint (warning)
  if (
    toPort.expectedUpstreamCategories &&
    toPort.expectedUpstreamCategories.length > 0 &&
    !toPort.expectedUpstreamCategories.includes(fromDef.category)
  ) {
    issues.push({
      severity: "warning",
      code: "category_hint",
      message: `Unusual upstream: ${fromDef.category}`,
      detail: `"${toDef.label}" is usually fed from ${toPort.expectedUpstreamCategories.join(
        ", "
      )}. Feeding it directly from a ${fromDef.category} node may work but often means a fusion/temporal step is missing.`,
    });
  }

  return issues;
}

// --- node-level report ---

export function validateNode(
  instanceId: string,
  state: GraphSlice
): NodeValidationReport {
  const node = nodeById(state, instanceId);
  const emptyReport: NodeValidationReport = {
    inputs: [],
    outputs: [],
    worstSeverity: "ok",
  };
  if (!node) return emptyReport;
  const def = getNodeDef(node.defId);
  if (!def) return emptyReport;

  let worst: "ok" | "warning" | "error" = "ok";
  const bumpWorst = (s: ValidationSeverity) => {
    if (s === "error") worst = "error";
    else if (s === "warning" && worst !== "error") worst = "warning";
  };

  const inputs: PortRequirementStatus[] = [];
  for (const port of def.ports) {
    if (port.type !== "input") continue;
    const incoming = state.connections.filter(
      (c) => c.toNode === instanceId && c.toPort === port.name
    );
    const required = port.required !== false; // default true
    const shape = effectiveShape(port);
    const expectedWidth = resolveWidth(port, node);

    const perConn = incoming.map((c) => {
      const from = nodeById(state, c.fromNode);
      const fromPort = from ? portOf(from, c.fromPort, "output") : undefined;
      const actualShape = fromPort ? effectiveShape(fromPort) : undefined;
      const actualWidth = from && fromPort ? resolveWidth(fromPort, from) : undefined;
      const issues = validateConnection(c, state);
      for (const i of issues) bumpWorst(i.severity);
      return {
        connId: c.id,
        fromNodeId: c.fromNode,
        fromNodeLabel: nodeLabel(from),
        fromPort: c.fromPort,
        actualShape,
        actualWidth,
        issues,
      };
    });

    const portIssues: ValidationIssue[] = [];
    if (required && incoming.length === 0) {
      portIssues.push({
        severity: "warning",
        code: "required_input_missing",
        message: "Required input not connected",
        detail: `"${def.label}" needs something feeding "${port.name}" (${port.dataType}${
          port.widthParam ? `, width ${port.widthParam}` : ""
        }).`,
      });
      bumpWorst("warning");
    }

    // Aggregate per-connection issue severities into the port-level status.
    const anyError = perConn.some((c) => c.issues.some((i) => i.severity === "error"));
    const anyWarning = perConn.some((c) =>
      c.issues.some((i) => i.severity === "warning")
    );
    let status: PortRequirementStatus["status"];
    if (anyError) status = "error";
    else if (incoming.length === 0 && required) status = "missing";
    else if (anyWarning) status = "warning";
    else if (incoming.length === 0 && !required) status = "ok";
    else status = "ok";

    inputs.push({
      portName: port.name,
      portLabel: port.name,
      dataType: port.dataType,
      shape,
      widthParam: port.widthParam,
      expectedWidth,
      required,
      multi: !!port.multi,
      multiSemantics: port.multi ? (port.multiSemantics ?? "concat") : undefined,
      connections: perConn,
      status,
      issues: portIssues,
    });
  }

  const outputs: OutputPortStatus[] = [];
  for (const port of def.ports) {
    if (port.type !== "output") continue;
    const outgoing = state.connections.filter(
      (c) => c.fromNode === instanceId && c.fromPort === port.name
    );
    const consumers: OutputConsumer[] = outgoing.map((c) => {
      const to = nodeById(state, c.toNode);
      const toPortDef = to ? portOf(to, c.toPort, "input") : undefined;
      const expectedShape = toPortDef ? effectiveShape(toPortDef) : undefined;
      const expectedWidth = to && toPortDef ? resolveWidth(toPortDef, to) : undefined;
      const issues = validateConnection(c, state);
      for (const i of issues) bumpWorst(i.severity);
      return {
        connId: c.id,
        toNodeId: c.toNode,
        toNodeLabel: nodeLabel(to),
        toPort: c.toPort,
        expectedShape,
        expectedWidth,
        issues,
      };
    });
    const anyError = consumers.some((c) => c.issues.some((i) => i.severity === "error"));
    const anyWarning = consumers.some((c) => c.issues.some((i) => i.severity === "warning"));
    const status: OutputPortStatus["status"] = anyError
      ? "error"
      : anyWarning
        ? "warning"
        : "ok";
    outputs.push({
      portName: port.name,
      dataType: port.dataType,
      shape: effectiveShape(port),
      widthParam: port.widthParam,
      width: resolveWidth(port, node),
      consumers,
      status,
    });
  }

  return { inputs, outputs, worstSeverity: worst };
}

// --- prospective (used for coloring the pending-drag line) ---

export function validateProspective(
  fromNodeId: string,
  fromPort: string,
  toNodeId: string,
  toPort: string,
  state: GraphSlice
): ValidationIssue[] {
  // Build a hypothetical state with the new edge included and run the standard check.
  const hypothetical: GraphSlice = {
    nodes: state.nodes,
    connections: [
      ...state.connections,
      {
        id: "__hypothetical__",
        fromNode: fromNodeId,
        fromPort,
        toNode: toNodeId,
        toPort,
      },
    ],
  };
  const conn = hypothetical.connections[hypothetical.connections.length - 1];
  return validateConnection(conn, hypothetical);
}

// Touch the registry so this module compiles cleanly even if NODE_REGISTRY is
// the only export used elsewhere.
void NODE_REGISTRY;
