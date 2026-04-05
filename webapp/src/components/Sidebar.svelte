<script lang="ts">
  import { getNodesByCategory } from "../lib/registry";
  import { CATEGORY_COLORS, CATEGORY_LABELS } from "../lib/types";

  const categories = getNodesByCategory();

  // Track which categories are expanded
  let expanded = $state<Record<string, boolean>>({
    feature_extractors: true,
    composition: true,
    fusion: true,
    temporal: true,
    heads: true,
  });

  function toggleCategory(cat: string) {
    expanded[cat] = !expanded[cat];
  }

  function onDragStart(e: DragEvent, nodeId: string) {
    e.dataTransfer?.setData("node-def-id", nodeId);
    e.dataTransfer!.effectAllowed = "copy";
  }
</script>

<aside class="sidebar">
  <div class="sidebar-header">Modules</div>
  {#each [...categories.entries()] as [category, nodes]}
    <div class="category">
      <button
        class="category-header"
        onclick={() => toggleCategory(category)}
      >
        <span
          class="category-dot"
          style="background: {CATEGORY_COLORS[
            category as keyof typeof CATEGORY_COLORS
          ]}"
        ></span>
        <span class="category-label"
          >{CATEGORY_LABELS[
            category as keyof typeof CATEGORY_LABELS
          ] ?? category}</span
        >
        <span class="chevron" class:open={expanded[category]}>&#9654;</span>
      </button>
      {#if expanded[category]}
        <div class="category-items">
          {#each nodes as node}
            <div
              class="module-item"
              draggable="true"
              ondragstart={(e) => onDragStart(e, node.id)}
              role="button"
              tabindex="0"
            >
              {node.label}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/each}
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    overflow-y: auto;
    user-select: none;
  }

  .sidebar-header {
    padding: 12px 16px 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
  }

  .category {
    margin-bottom: 2px;
  }

  .category-header {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 16px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
    border-radius: 0;
  }

  .category-header:hover {
    background: var(--bg-surface-hover);
  }

  .category-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .category-label {
    flex: 1;
  }

  .chevron {
    font-size: 9px;
    color: var(--text-muted);
    transition: transform 0.15s;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .category-items {
    padding: 2px 0;
  }

  .module-item {
    padding: 6px 16px 6px 32px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: grab;
    border-radius: 4px;
    margin: 0 8px;
    transition: background 0.1s, color 0.1s;
  }

  .module-item:hover {
    background: var(--bg-surface);
    color: var(--text-primary);
  }

  .module-item:active {
    cursor: grabbing;
  }
</style>
