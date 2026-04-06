<script lang="ts">
  import { getNodeDef } from "../lib/registry";
  import {
    graphState,
    selectNode,
    moveNode,
    updateNodeParam,
    removeNode,
    removeSelectedNodes,
    startConnection,
    finishConnection,
  } from "../lib/state.svelte";
  import { CATEGORY_COLORS, type NodeInstance, type PortDef } from "../lib/types";

  const PORT_COLORS: Record<string, string> = {
    data: "var(--port-data)",
    embedding: "var(--port-embedding)",
    tensor: "var(--port-tensor)",
    graph: "var(--port-graph)",
  };

  function portColor(port: PortDef): string {
    return PORT_COLORS[port.dataType] ?? "var(--port-embedding)";
  }

  interface Props {
    node: NodeInstance;
    zoom: number;
  }

  let { node, zoom }: Props = $props();

  let def = $derived(getNodeDef(node.defId)!);
  let isSelected = $derived(graphState.selectedNodeIds.has(node.instanceId));
  let categoryColor = $derived(CATEGORY_COLORS[def.category]);

  let inputPorts = $derived(def.ports.filter((p) => p.type === "input"));
  let outputPorts = $derived(def.ports.filter((p) => p.type === "output"));

  const NODE_WIDTH = 200;
  const HEADER_HEIGHT = 32;
  const PORT_ROW_HEIGHT = 22;
  const PARAM_ROW_HEIGHT = 26;
  const PADDING_BOTTOM = 12;
  const OVERFLOW_PAD = 6; // extra padding for border/shadow not to clip

  let portsHeight = $derived(
    Math.max(inputPorts.length, outputPorts.length) * PORT_ROW_HEIGHT
  );
  let paramsHeight = $derived(
    def.params.length * PARAM_ROW_HEIGHT + (def.params.length > 0 ? 8 : 0)
  );
  let bodyHeight = $derived(portsHeight + paramsHeight + PADDING_BOTTOM + 8);
  let totalHeight = $derived(HEADER_HEIGHT + bodyHeight);

  // Dragging state
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let nodeStartX = 0;
  let nodeStartY = 0;
  let dragGroupStart: { id: string; x: number; y: number }[] = [];

  function handleMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).closest(".port, input, select")) return;
    e.preventDefault();
    e.stopPropagation();
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    nodeStartX = node.x;
    nodeStartY = node.y;

    // Shift+click toggles multi-select; plain click replaces selection
    // But if this node is already in the selection, keep the group for dragging
    if (e.shiftKey) {
      selectNode(node.instanceId, true);
    } else if (!graphState.selectedNodeIds.has(node.instanceId)) {
      selectNode(node.instanceId);
    }

    // Snapshot all selected node positions for group drag
    dragGroupStart = [];
    for (const n of graphState.nodes) {
      if (graphState.selectedNodeIds.has(n.instanceId)) {
        dragGroupStart.push({ id: n.instanceId, x: n.x, y: n.y });
      }
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }

  function handleMouseMove(e: MouseEvent) {
    if (!isDragging) return;
    const dx = (e.clientX - dragStartX) / zoom;
    const dy = (e.clientY - dragStartY) / zoom;
    // Move all selected nodes together
    for (const start of dragGroupStart) {
      moveNode(start.id, start.x + dx, start.y + dy);
    }
  }

  function handleMouseUp() {
    isDragging = false;
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (
      (e.key === "Delete" || e.key === "Backspace") &&
      isSelected &&
      !(e.target instanceof HTMLInputElement) &&
      !(e.target instanceof HTMLSelectElement)
    ) {
      if (graphState.selectedNodeIds.size > 1) {
        removeSelectedNodes();
      } else {
        removeNode(node.instanceId);
      }
    }
  }

  function getPortY(index: number): number {
    return HEADER_HEIGHT + 12 + index * PORT_ROW_HEIGHT;
  }

  function handleOutputPortMouseDown(e: MouseEvent, portName: string) {
    e.stopPropagation();
    e.preventDefault();
    const portIndex = outputPorts.findIndex((p) => p.name === portName);
    const portY = getPortY(portIndex);
    startConnection(
      node.instanceId,
      portName,
      node.x + NODE_WIDTH,
      node.y + portY
    );
  }

  function handleOutputPortClick(e: MouseEvent, portName: string) {
    e.stopPropagation();
    // If no pending connection, start one (click-to-connect mode)
    if (!graphState.pendingConnection) {
      const portIndex = outputPorts.findIndex((p) => p.name === portName);
      const portY = getPortY(portIndex);
      startConnection(
        node.instanceId,
        portName,
        node.x + NODE_WIDTH,
        node.y + portY
      );
    }
  }

  function handleInputPortMouseUp(e: MouseEvent, portName: string) {
    e.stopPropagation();
    if (graphState.pendingConnection) {
      finishConnection(node.instanceId, portName);
    }
  }

  function handleInputPortClick(e: MouseEvent, portName: string) {
    e.stopPropagation();
    if (graphState.pendingConnection) {
      finishConnection(node.instanceId, portName);
    }
  }

  function handleParamChange(paramName: string, value: string, type: string) {
    if (type === "number") {
      const num = parseFloat(value);
      if (!isNaN(num)) updateNodeParam(node.instanceId, paramName, num);
    } else {
      updateNodeParam(node.instanceId, paramName, value);
    }
  }

  // Port position helpers exposed for connection rendering
  export function getInputPortPosition(
    portName: string
  ): { x: number; y: number } | null {
    const idx = inputPorts.findIndex((p) => p.name === portName);
    if (idx === -1) return null;
    return { x: node.x, y: node.y + getPortY(idx) };
  }

  export function getOutputPortPosition(
    portName: string
  ): { x: number; y: number } | null {
    const idx = outputPorts.findIndex((p) => p.name === portName);
    if (idx === -1) return null;
    return { x: node.x + NODE_WIDTH, y: node.y + getPortY(idx) };
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<g transform="translate({node.x - OVERFLOW_PAD}, {node.y - OVERFLOW_PAD})">
  <foreignObject width={NODE_WIDTH + OVERFLOW_PAD * 2} height={totalHeight + OVERFLOW_PAD * 2}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="node"
      class:selected={isSelected}
      onmousedown={handleMouseDown}
      style="--cat-color: {categoryColor}; width: {NODE_WIDTH}px; margin: {OVERFLOW_PAD}px;"
    >
      <!-- Header -->
      <div class="node-header">
        <span class="node-title">{def.label}</span>
      </div>

      <!-- Body -->
      <div class="node-body">
        <!-- Ports -->
        <div class="ports-section">
          <div class="ports-col left">
            {#each inputPorts as port, i}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <div class="port-row">
                <div
                  class="port input"
                  onmousedown={(e) => e.stopPropagation()}
                  onclick={(e) => handleInputPortClick(e, port.name)}
                  title={port.name}
                ></div>
                <span class="port-label">{port.name}</span>
              </div>
            {/each}
          </div>
          <div class="ports-col right">
            {#each outputPorts as port, i}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <div class="port-row">
                <span class="port-label">{port.name}</span>
                <div
                  class="port output"
                  onmousedown={(e) => e.stopPropagation()}
                  onclick={(e) => handleOutputPortClick(e, port.name)}
                  title={port.name}
                ></div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Params -->
        {#if def.params.length > 0}
          <div class="params-section">
            {#each def.params as param}
              <div class="param-row">
                <span class="param-name">{param.name}</span>
                {#if param.type === "select" && param.options}
                  <select
                    value={node.params[param.name]}
                    onchange={(e) =>
                      handleParamChange(
                        param.name,
                        (e.target as HTMLSelectElement).value,
                        "string"
                      )}
                  >
                    {#each param.options as opt}
                      <option value={opt}>{opt}</option>
                    {/each}
                  </select>
                {:else}
                  <input
                    type={param.type === "number" ? "number" : "text"}
                    value={node.params[param.name]}
                    onchange={(e) =>
                      handleParamChange(
                        param.name,
                        (e.target as HTMLInputElement).value,
                        param.type
                      )}
                    onmousedown={(e) => e.stopPropagation()}
                  />
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </foreignObject>

  <!-- Port circles in SVG space for connection endpoints -->
  {#each inputPorts as port, i}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <circle
      cx={OVERFLOW_PAD}
      cy={getPortY(i) + OVERFLOW_PAD}
      r="5"
      fill={portColor(port)}
      stroke="var(--bg-primary)"
      stroke-width="2"
      style="cursor: pointer; pointer-events: all;"
      onclick={(e) => { e.stopPropagation(); handleInputPortClick(e, port.name); }}
      onmouseup={(e) => { e.stopPropagation(); handleInputPortMouseUp(e, port.name); }}
    />
  {/each}
  {#each outputPorts as port, i}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <circle
      cx={NODE_WIDTH + OVERFLOW_PAD}
      cy={getPortY(i) + OVERFLOW_PAD}
      r="5"
      fill={portColor(port)}
      stroke="var(--bg-primary)"
      stroke-width="2"
      style="cursor: pointer; pointer-events: all;"
      onmousedown={(e) => { handleOutputPortMouseDown(e, port.name); }}
      onclick={(e) => { e.stopPropagation(); handleOutputPortClick(e, port.name); }}
    />
  {/each}
</g>

<style>
  .node {
    background: var(--bg-node);
    border: 1.5px solid var(--border-color);
    border-radius: var(--border-radius);
    overflow: hidden;
    cursor: grab;
    user-select: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .node:hover {
    border-color: var(--border-active);
  }

  .node.selected {
    border-color: var(--cat-color);
    box-shadow: 0 0 0 1px var(--cat-color), 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  .node:active {
    cursor: grabbing;
  }

  .node-header {
    padding: 7px 12px;
    background: color-mix(in srgb, var(--cat-color) 15%, var(--bg-node));
    border-bottom: 1px solid var(--border-color);
  }

  .node-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .node-body {
    padding: 6px 12px;
  }

  .ports-section {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .ports-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ports-col.right {
    align-items: flex-end;
  }

  .port-row {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 18px;
  }

  .port {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: transparent;
    cursor: pointer;
  }

  .port-label {
    font-size: 10px;
    color: var(--text-muted);
  }

  .params-section {
    border-top: 1px solid var(--border-color);
    padding-top: 6px;
    margin-top: 2px;
  }

  .param-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 22px;
  }

  .param-name {
    font-size: 10px;
    color: var(--text-secondary);
  }

  .param-row input,
  .param-row select {
    width: 60px;
    font-size: 11px;
    padding: 1px 4px;
  }
</style>
