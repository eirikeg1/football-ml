<script lang="ts">
  import {
    graphState,
    selectConnection,
    removeConnection,
    togglePopover,
  } from "../lib/state.svelte";
  import { validateConnection } from "../lib/validation";
  import type { ValidationIssue } from "../lib/types";

  interface Props {
    id: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    pending?: boolean;
  }

  let { id, x1, y1, x2, y2, pending = false }: Props = $props();

  let isSelected = $derived(graphState.selectedConnectionId === id);

  // Bezier control points: horizontal offset based on distance
  let dx = $derived(Math.abs(x2 - x1));
  let offset = $derived(Math.max(50, dx * 0.4));
  let path = $derived(
    `M ${x1} ${y1} C ${x1 + offset} ${y1}, ${x2 - offset} ${y2}, ${x2} ${y2}`
  );

  // Midpoint of the cubic bezier at t=0.5
  // B(0.5) = 0.125·P0 + 0.375·P1 + 0.375·P2 + 0.125·P3
  let midX = $derived(0.125 * x1 + 0.375 * (x1 + offset) + 0.375 * (x2 - offset) + 0.125 * x2);
  let midY = $derived(0.125 * y1 + 0.375 * y1 + 0.375 * y2 + 0.125 * y2);

  // Validation issues for this existing connection (pending has no record in state).
  let issues: ValidationIssue[] = $derived.by(() => {
    if (pending) return [];
    const conn = graphState.connections.find((c) => c.id === id);
    if (!conn) return [];
    return validateConnection(conn, graphState);
  });

  let severity: "ok" | "warning" | "error" = $derived(
    issues.some((i) => i.severity === "error")
      ? "error"
      : issues.some((i) => i.severity === "warning")
        ? "warning"
        : "ok"
  );

  let strokeColor = $derived(
    severity === "error"
      ? isSelected
        ? "var(--error-strong)"
        : "var(--error)"
      : severity === "warning"
        ? isSelected
          ? "var(--warning-strong)"
          : "var(--warning)"
        : isSelected
          ? "var(--connection-active)"
          : pending
            ? "var(--text-muted)"
            : "var(--connection-color)"
  );

  function toggleIssues(e: MouseEvent) {
    e.stopPropagation();
    e.preventDefault();
    togglePopover({ kind: "connection-issues", connId: id });
  }

  function handleClick(e: MouseEvent) {
    e.stopPropagation();
    if (!pending) {
      selectConnection(id);
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if ((e.key === "Delete" || e.key === "Backspace") && isSelected) {
      removeConnection(id);
    }
  }

  let badgeColor = $derived(severity === "error" ? "var(--error)" : "var(--warning)");
</script>

<g
  class="connection"
  class:selected={isSelected}
  class:pending
  class:has-error={severity === "error"}
  class:has-warning={severity === "warning"}
>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <!-- Wider invisible hit area -->
  <path
    d={path}
    fill="none"
    stroke="transparent"
    stroke-width="12"
    onclick={handleClick}
    style="cursor: pointer;"
  />
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <!-- Visible path -->
  <path
    d={path}
    fill="none"
    stroke={strokeColor}
    stroke-width={isSelected ? 2.5 : 2}
    stroke-dasharray={pending ? "6 4" : "none"}
    onclick={handleClick}
    style="cursor: pointer; transition: stroke 0.15s;"
  />

  {#if !pending && severity !== "ok"}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <g
      class="issue-badge"
      transform="translate({midX}, {midY})"
      onclick={toggleIssues}
      style="cursor: pointer;"
    >
      <circle r="9" fill={badgeColor} stroke="var(--bg-primary)" stroke-width="2" />
      <text
        x="0"
        y="0"
        text-anchor="middle"
        dominant-baseline="central"
        fill="#fff"
        font-size="12"
        font-weight="700"
        font-family="Georgia, 'Times New Roman', serif"
        style="pointer-events: none; user-select: none;"
      >!</text>
    </g>

  {/if}
</g>

<svelte:window onkeydown={handleKeydown} />

<style>
  .connection path {
    pointer-events: stroke;
  }

  .issue-badge circle {
    transition: r 0.15s;
  }

  .issue-badge:hover circle {
    r: 10;
  }
</style>
