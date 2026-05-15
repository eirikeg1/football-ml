<script lang="ts">
  import {
    graphState,
    addNode,
    cancelConnection,
    updatePendingConnection,
    selectNode,
    selectNodes,
    selectConnection,
    closePopover,
  } from "../lib/state.svelte";
  import { getNodeDef } from "../lib/registry";
  import { validateConnection } from "../lib/validation";
  import GraphNode from "./GraphNode.svelte";
  import Connection from "./Connection.svelte";

  const NODE_WIDTH = 200;
  const HEADER_HEIGHT = 32;
  const PORT_ROW_HEIGHT = 22;
  const PARAM_ROW_HEIGHT = 26;

  // Pan & zoom state
  let panX = $state(0);
  let panY = $state(0);
  let zoom = $state(1);
  let isPanning = $state(false);
  let panStartX = 0;
  let panStartY = 0;
  let panStartPanX = 0;
  let panStartPanY = 0;
  let spaceHeld = $state(false);

  // Box select state
  let isBoxSelecting = $state(false);
  let boxStart = $state({ x: 0, y: 0 });
  let boxEnd = $state({ x: 0, y: 0 });

  let boxRect = $derived({
    x: Math.min(boxStart.x, boxEnd.x),
    y: Math.min(boxStart.y, boxEnd.y),
    width: Math.abs(boxEnd.x - boxStart.x),
    height: Math.abs(boxEnd.y - boxStart.y),
  });

  let svgEl: SVGSVGElement;

  // Convert screen coords to graph coords
  function screenToGraph(clientX: number, clientY: number): { x: number; y: number } {
    const rect = svgEl.getBoundingClientRect();
    return {
      x: (clientX - rect.left - panX) / zoom,
      y: (clientY - rect.top - panY) / zoom,
    };
  }

  // Wheel zoom (centered on cursor)
  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const rect = svgEl.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY > 0 ? 0.92 : 1.08;
    const newZoom = Math.max(0.15, Math.min(3, zoom * zoomFactor));

    // Adjust pan to keep mouse position stable
    panX = mouseX - (mouseX - panX) * (newZoom / zoom);
    panY = mouseY - (mouseY - panY) * (newZoom / zoom);
    zoom = newZoom;
  }

  function getNodeHeight(node: { defId: string }): number {
    const def = getNodeDef(node.defId);
    if (!def) return 60;
    const ports = Math.max(
      def.ports.filter((p) => p.type === "input").length,
      def.ports.filter((p) => p.type === "output").length
    );
    return HEADER_HEIGHT + ports * PORT_ROW_HEIGHT + def.params.length * PARAM_ROW_HEIGHT + 28;
  }

  // Pan: middle-click or space+left-click
  function handleMouseDown(e: MouseEvent) {
    if (e.button === 1 || (e.button === 0 && spaceHeld)) {
      e.preventDefault();
      isPanning = true;
      panStartX = e.clientX;
      panStartY = e.clientY;
      panStartPanX = panX;
      panStartPanY = panY;
      return;
    }

    // Left click on empty canvas area
    if (e.button === 0) {
      // Check if clicking on the SVG background (not on a node/connection)
      const target = e.target as Element;
      const isCanvas = target === svgEl || target.tagName === "rect" || target.closest(".canvas-bg");

      if (isCanvas) {
        if (graphState.pendingConnection) {
          cancelConnection();
          return;
        }

        // Start box select
        const pos = screenToGraph(e.clientX, e.clientY);
        isBoxSelecting = true;
        boxStart = { x: pos.x, y: pos.y };
        boxEnd = { x: pos.x, y: pos.y };

        if (!e.shiftKey) {
          selectNode(null);
          selectConnection(null);
          closePopover();
        }
      }
    }
  }

  function handleMouseMove(e: MouseEvent) {
    if (isPanning) {
      panX = panStartPanX + (e.clientX - panStartX);
      panY = panStartPanY + (e.clientY - panStartY);
      return;
    }

    if (isBoxSelecting) {
      const pos = screenToGraph(e.clientX, e.clientY);
      boxEnd = { x: pos.x, y: pos.y };
      return;
    }

    // Update pending connection line
    if (graphState.pendingConnection) {
      const pos = screenToGraph(e.clientX, e.clientY);
      updatePendingConnection(pos.x, pos.y);
    }
  }

  function handleMouseUp(e: MouseEvent) {
    if (isPanning) {
      isPanning = false;
      return;
    }

    if (isBoxSelecting) {
      isBoxSelecting = false;

      // Find nodes that intersect the selection box
      const r = boxRect;
      if (r.width < 3 && r.height < 3) {
        // Tiny box = just a click, deselect handled in mouseDown
        return;
      }

      const hits: string[] = [];
      for (const node of graphState.nodes) {
        const nh = getNodeHeight(node);
        // Check AABB intersection
        if (
          node.x < r.x + r.width &&
          node.x + NODE_WIDTH > r.x &&
          node.y < r.y + r.height &&
          node.y + nh > r.y
        ) {
          hits.push(node.instanceId);
        }
      }

      if (e.shiftKey) {
        // Add to existing selection
        const combined = new Set(graphState.selectedNodeIds);
        for (const id of hits) combined.add(id);
        selectNodes([...combined]);
      } else {
        selectNodes(hits);
      }
      return;
    }

    // Cancel pending connection if released on empty canvas (not on an input port)
    if (graphState.pendingConnection) {
      cancelConnection();
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.code === "Space" && !(e.target instanceof HTMLInputElement)) {
      e.preventDefault();
      spaceHeld = true;
    }
    if (e.key === "Escape") {
      if (graphState.pendingConnection) {
        cancelConnection();
      } else if (isBoxSelecting) {
        isBoxSelecting = false;
      } else {
        selectNode(null);
        selectConnection(null);
      }
    }
  }

  function handleKeyUp(e: KeyboardEvent) {
    if (e.code === "Space") {
      spaceHeld = false;
    }
  }

  // Drop from sidebar
  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    e.dataTransfer!.dropEffect = "copy";
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    const defId = e.dataTransfer?.getData("node-def-id");
    if (!defId) return;
    const pos = screenToGraph(e.clientX, e.clientY);
    addNode(defId, pos.x - 100, pos.y - 20);
  }

  // Connection endpoint positions
  function getPortPos(
    nodeInstanceId: string,
    portName: string,
    portType: "input" | "output"
  ): { x: number; y: number } {
    const node = graphState.nodes.find((n) => n.instanceId === nodeInstanceId);
    if (!node) return { x: 0, y: 0 };
    const def = getNodeDef(node.defId);
    if (!def) return { x: 0, y: 0 };

    const ports = def.ports.filter((p) => p.type === portType);
    const idx = ports.findIndex((p) => p.name === portName);
    if (idx === -1) return { x: 0, y: 0 };

    const NODE_WIDTH = 200;
    const HEADER_HEIGHT = 32;
    const PORT_ROW_HEIGHT = 22;
    const portY = HEADER_HEIGHT + 12 + idx * PORT_ROW_HEIGHT;

    return {
      x: node.x + (portType === "output" ? NODE_WIDTH : 0),
      y: node.y + portY,
    };
  }
</script>

<svelte:window onkeydown={handleKeyDown} onkeyup={handleKeyUp} />

<div
  class="canvas-container"
  class:panning={isPanning || spaceHeld}
>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <svg
    bind:this={svgEl}
    class="canvas"
    onwheel={handleWheel}
    onmousedown={handleMouseDown}
    onmousemove={handleMouseMove}
    onmouseup={handleMouseUp}
    ondragover={handleDragOver}
    ondrop={handleDrop}
  >
    <!-- Grid pattern -->
    <defs>
      <pattern id="grid-small" width="20" height="20" patternUnits="userSpaceOnUse"
        x={panX % (20 * zoom)} y={panY % (20 * zoom)}
        patternTransform="scale({zoom})"
      >
        <circle cx="10" cy="10" r="0.5" fill="var(--grid-color)" />
      </pattern>
      <pattern id="grid-large" width="100" height="100" patternUnits="userSpaceOnUse"
        x={panX % (100 * zoom)} y={panY % (100 * zoom)}
        patternTransform="scale({zoom})"
      >
        <circle cx="50" cy="50" r="0.8" fill="var(--grid-color-major)" />
      </pattern>
    </defs>

    <rect class="canvas-bg" width="100%" height="100%" fill="var(--bg-primary)" />
    <rect class="canvas-bg" width="100%" height="100%" fill="url(#grid-small)" />
    <rect class="canvas-bg" width="100%" height="100%" fill="url(#grid-large)" />

    <!-- Transformed group for pan/zoom -->
    <g transform="translate({panX}, {panY}) scale({zoom})">
      <!-- Connections -->
      {#each graphState.connections as conn (conn.id)}
        {@const from = getPortPos(conn.fromNode, conn.fromPort, "output")}
        {@const to = getPortPos(conn.toNode, conn.toPort, "input")}
        <Connection
          id={conn.id}
          x1={from.x}
          y1={from.y}
          x2={to.x}
          y2={to.y}
        />
      {/each}

      <!-- Pending connection -->
      {#if graphState.pendingConnection}
        <Connection
          id="__pending"
          x1={graphState.pendingConnection.fromX}
          y1={graphState.pendingConnection.fromY}
          x2={graphState.pendingConnection.mouseX}
          y2={graphState.pendingConnection.mouseY}
          pending={true}
        />
      {/if}

      <!-- Nodes -->
      {#each graphState.nodes as node (node.instanceId)}
        <GraphNode {node} {zoom} />
      {/each}

      <!-- Box selection rectangle -->
      {#if isBoxSelecting && boxRect.width > 1}
        <rect
          x={boxRect.x}
          y={boxRect.y}
          width={boxRect.width}
          height={boxRect.height}
          fill="rgba(74, 158, 255, 0.08)"
          stroke="var(--accent)"
          stroke-width={1.5 / zoom}
          stroke-dasharray="{4 / zoom} {3 / zoom}"
          rx={3 / zoom}
        />
      {/if}

      <!-- Popover overlay: rendered last so it always paints on top of nodes/edges -->
      {#if graphState.openPopover}
        {@const pop = graphState.openPopover}
        {#if pop.kind === "node-info"}
          {@const node = graphState.nodes.find((n) => n.instanceId === pop.nodeId)}
          {@const def = node ? getNodeDef(node.defId) : null}
          {#if node && def}
            <foreignObject
              x={node.x + NODE_WIDTH + 10}
              y={node.y}
              width="290"
              height="420"
              style="overflow: visible; pointer-events: none;"
            >
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <div
                class="popover info-popover"
                onmousedown={(e) => e.stopPropagation()}
                onclick={(e) => e.stopPropagation()}
                style="pointer-events: auto;"
              >
                {#each def.description.split('\n') as line}
                  {#if line.trim() === ''}
                    <div class="info-gap"></div>
                  {:else}
                    <p class="info-line">{line}</p>
                  {/if}
                {/each}
                {#if def.hints?.placement || (def.hints?.tips && def.hints.tips.length > 0)}
                  <div class="info-gap"></div>
                  {#if def.hints.placement}
                    <p class="info-hint"><span class="info-hint-label">Placement</span> {def.hints.placement}</p>
                  {/if}
                  {#if def.hints.tips && def.hints.tips.length > 0}
                    <ul class="info-tips">
                      {#each def.hints.tips as tip}
                        <li>{tip}</li>
                      {/each}
                    </ul>
                  {/if}
                {/if}
                <button class="popover-close" onclick={closePopover}>close</button>
              </div>
            </foreignObject>
          {/if}
        {:else if pop.kind === "connection-issues"}
          {@const conn = graphState.connections.find((c) => c.id === pop.connId)}
          {#if conn}
            {@const from = getPortPos(conn.fromNode, conn.fromPort, "output")}
            {@const to = getPortPos(conn.toNode, conn.toPort, "input")}
            {@const offset = Math.max(50, Math.abs(to.x - from.x) * 0.4)}
            {@const midX = 0.125 * from.x + 0.375 * (from.x + offset) + 0.375 * (to.x - offset) + 0.125 * to.x}
            {@const midY = 0.125 * from.y + 0.375 * from.y + 0.375 * to.y + 0.125 * to.y}
            {@const issues = validateConnection(conn, graphState)}
            <foreignObject
              x={midX + 12}
              y={midY - 12}
              width="310"
              height="320"
              style="overflow: visible; pointer-events: none;"
            >
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <div
                class="popover issue-popover"
                onmousedown={(e) => e.stopPropagation()}
                onclick={(e) => e.stopPropagation()}
                style="pointer-events: auto;"
              >
                {#each issues as issue}
                  <div class="issue-row" class:error={issue.severity === "error"} class:warning={issue.severity === "warning"}>
                    <div class="issue-title">{issue.message}</div>
                    {#if issue.detail}
                      <div class="issue-detail">{issue.detail}</div>
                    {/if}
                  </div>
                {/each}
                <button class="popover-close" onclick={closePopover}>close</button>
              </div>
            </foreignObject>
          {/if}
        {/if}
      {/if}
    </g>
  </svg>
</div>

<style>
  .canvas-container {
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  .canvas-container.panning {
    cursor: grab;
  }

  .canvas-container.panning:active {
    cursor: grabbing;
  }

  .canvas {
    width: 100%;
    height: 100%;
    display: block;
  }

  .popover {
    background: #16213e;
    border: 1px solid #4a6fa5;
    border-radius: 8px;
    padding: 12px 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    cursor: default;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .info-popover {
    width: 280px;
  }

  .info-line {
    font-size: 11.5px;
    line-height: 1.55;
    color: #8892a4;
    margin: 0;
  }

  .info-gap {
    height: 4px;
  }

  .info-hint {
    font-size: 11.5px;
    line-height: 1.55;
    color: var(--text-primary);
    margin: 0;
    padding: 6px 8px;
    border-left: 3px solid var(--accent);
    background: rgba(74, 158, 255, 0.06);
    border-radius: 3px;
  }

  .info-hint-label {
    font-weight: 600;
    color: var(--accent);
    margin-right: 4px;
  }

  .info-tips {
    margin: 6px 0 0;
    padding-left: 18px;
    font-size: 11px;
    line-height: 1.5;
    color: #8892a4;
  }

  .info-tips li {
    margin-bottom: 2px;
  }

  .issue-popover {
    width: 300px;
  }

  .issue-row {
    padding: 6px 8px;
    border-left: 3px solid var(--border-color);
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.02);
  }

  .issue-row.error {
    border-left-color: var(--error);
    background: rgba(229, 72, 77, 0.08);
  }

  .issue-row.warning {
    border-left-color: var(--warning);
    background: rgba(245, 166, 35, 0.08);
  }

  .issue-title {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 3px;
  }

  .issue-detail {
    font-size: 11px;
    line-height: 1.5;
    color: var(--text-secondary);
  }

  .popover-close {
    align-self: flex-end;
    font-size: 10px;
    padding: 2px 10px;
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-muted);
    margin-top: 2px;
  }

  .popover-close:hover {
    color: var(--text-primary);
    border-color: var(--border-active);
  }
</style>
