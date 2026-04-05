<script lang="ts">
  import { graphState, selectConnection, removeConnection } from "../lib/state.svelte";

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
</script>

<g
  class="connection"
  class:selected={isSelected}
  class:pending
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
    stroke={isSelected ? "var(--connection-active)" : pending ? "var(--text-muted)" : "var(--connection-color)"}
    stroke-width={isSelected ? 2.5 : 2}
    stroke-dasharray={pending ? "6 4" : "none"}
    onclick={handleClick}
    style="cursor: pointer; transition: stroke 0.15s;"
  />
</g>

<svelte:window onkeydown={handleKeydown} />

<style>
  .connection path {
    pointer-events: stroke;
  }
</style>
