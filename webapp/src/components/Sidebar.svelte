<script lang="ts">
  import { getNodesByCategory } from "../lib/registry";
  import { CATEGORY_COLORS, CATEGORY_LABELS, type Category } from "../lib/types";

  const categories = getNodesByCategory();

  let expanded = $state<Record<string, boolean>>({
    data_sources: true,
    augmentation: true,
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

  function catColor(category: string): string {
    return CATEGORY_COLORS[category as Category] ?? "var(--text-muted)";
  }

  function catLabel(category: string): string {
    return CATEGORY_LABELS[category as Category] ?? category;
  }
</script>

<aside class="sidebar">
  <div class="sidebar-title">Modules</div>
  <div class="sidebar-scroll">
    {#each [...categories.entries()] as [category, nodes]}
      <div class="category">
        <button
          class="category-header"
          onclick={() => toggleCategory(category)}
        >
          <span class="category-indicator" style="background: {catColor(category)}"></span>
          <span class="category-label">{catLabel(category)}</span>
          <span class="category-count">{nodes.length}</span>
          <span class="chevron" class:open={expanded[category]}>
            <svg width="10" height="10" viewBox="0 0 10 10">
              <path d="M3 1.5 L7 5 L3 8.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        {#if expanded[category]}
          <div class="category-items">
            {#each nodes as node}
              <div
                class="module-item"
                class:not-implemented={node.implemented === false}
                draggable="true"
                ondragstart={(e) => onDragStart(e, node.id)}
                role="button"
                tabindex="0"
                title={node.description.split('\n')[0]}
                style="--cat-color: {catColor(category)}"
              >
                <span class="module-stripe"></span>
                <span class="module-label">{node.label}</span>
                {#if node.implemented === false}
                  <span class="coming-soon-badge">Soon</span>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    user-select: none;
  }

  .sidebar-title {
    padding: 14px 16px 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
  }

  .sidebar-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 6px 0;
  }

  .category {
    margin-bottom: 2px;
  }

  .category-header {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 12px 7px 14px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 12px;
    font-weight: 600;
    text-align: left;
    cursor: pointer;
    border-radius: 0;
    transition: background 0.1s;
  }

  .category-header:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .category-indicator {
    width: 3px;
    height: 16px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .category-label {
    flex: 1;
  }

  .category-count {
    font-size: 10px;
    font-weight: 500;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    padding: 1px 6px;
    border-radius: 8px;
    min-width: 20px;
    text-align: center;
  }

  .chevron {
    color: var(--text-muted);
    transition: transform 0.2s ease;
    display: flex;
    align-items: center;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .category-items {
    padding: 3px 8px 6px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .module-item {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 6px 10px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: grab;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid transparent;
    transition: background 0.12s, border-color 0.12s, color 0.12s, box-shadow 0.12s;
  }

  .module-item:hover {
    background: var(--bg-surface);
    border-color: var(--border-color);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  }

  .module-item:active {
    cursor: grabbing;
    background: var(--bg-surface-hover);
    border-color: color-mix(in srgb, var(--cat-color) 40%, var(--border-color));
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  }

  .module-stripe {
    width: 3px;
    height: 14px;
    border-radius: 1.5px;
    background: var(--cat-color);
    opacity: 0.5;
    flex-shrink: 0;
    margin-right: 9px;
    transition: opacity 0.12s;
  }

  .module-item:hover .module-stripe {
    opacity: 0.85;
  }

  .module-item.not-implemented {
    opacity: 0.5;
  }

  .module-item.not-implemented:hover {
    opacity: 0.7;
  }

  .module-label {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .coming-soon-badge {
    font-size: 9px;
    font-weight: 600;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.06);
    padding: 1px 6px;
    border-radius: 4px;
    flex-shrink: 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
</style>
