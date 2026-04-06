<script lang="ts">
  import {
    graphState,
    addNode,
    cancelConnection,
    updatePendingConnection,
    selectNode,
    selectNodes,
    selectConnection,
  } from "../lib/state.svelte";
  import { getNodeDef } from "../lib/registry";
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
</style>
