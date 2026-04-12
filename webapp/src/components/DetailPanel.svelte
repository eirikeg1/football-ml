<script lang="ts">
  import { graphState, getSelectedNode } from "../lib/state.svelte";
  import { getNodeDef } from "../lib/registry";
  import { CATEGORY_COLORS, CATEGORY_LABELS, type Category } from "../lib/types";
  import SqlitePanel from "./detail-panels/SqlitePanel.svelte";
  import CsvPanel from "./detail-panels/CsvPanel.svelte";
  import TableSelectorPanel from "./detail-panels/TableSelectorPanel.svelte";
  import MaterializationPanel from "./detail-panels/MaterializationPanel.svelte";

  let collapsed = $state(false);
  let selectedNode = $derived(getSelectedNode());
  let def = $derived(selectedNode ? getNodeDef(selectedNode.defId) : null);
  let categoryColor = $derived(
    def ? CATEGORY_COLORS[def.category] : "var(--text-muted)"
  );
  let categoryLabel = $derived(
    def ? CATEGORY_LABELS[def.category] : ""
  );

  function toggleCollapse() {
    collapsed = !collapsed;
  }
</script>

{#if selectedNode && def}
  <aside class="detail-panel" class:collapsed>
    <button class="collapse-btn" onclick={toggleCollapse} title={collapsed ? "Expand panel" : "Collapse panel"}>
      <svg width="10" height="10" viewBox="0 0 10 10">
        <path
          d={collapsed ? "M3 1.5 L7 5 L3 8.5" : "M7 1.5 L3 5 L7 8.5"}
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    {#if !collapsed}
      <div class="panel-scroll">
        <!-- Header -->
        <div class="panel-header">
          <span class="category-badge" style="background: {categoryColor}">{categoryLabel}</span>
          <h3 class="node-label">{def.label}</h3>
          <p class="node-description">{def.description.split('\n')[0]}</p>
        </div>

        <!-- Ports summary -->
        <div class="section">
          <div class="section-title">Ports</div>
          <div class="ports-list">
            {#each def.ports as port}
              <div class="port-item">
                <span class="port-direction">{port.type === "input" ? "IN" : "OUT"}</span>
                <span class="port-name">{port.name}</span>
                <span class="port-type">{port.dataType}</span>
              </div>
            {/each}
          </div>
        </div>

        <!-- Inline params summary -->
        {#if def.params.length > 0}
          <div class="section">
            <div class="section-title">Parameters</div>
            <div class="params-list">
              {#each def.params as param}
                <div class="param-item">
                  <span class="param-name">{param.name}</span>
                  <span class="param-value">{selectedNode.params[param.name]}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Detail panel dispatch -->
        {#if def.detailPanel === "datasource_sqlite"}
          <SqlitePanel node={selectedNode} />
        {:else if def.detailPanel === "datasource_csv"}
          <CsvPanel node={selectedNode} />
        {:else if def.detailPanel === "table_selector"}
          <TableSelectorPanel node={selectedNode} />
        {:else if def.detailPanel === "materialization"}
          <MaterializationPanel node={selectedNode} />
        {/if}
      </div>
    {/if}
  </aside>
{/if}

<style>
  .detail-panel {
    width: var(--detail-panel-width);
    background: var(--bg-secondary);
    border-left: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    position: relative;
    flex-shrink: 0;
  }

  .detail-panel.collapsed {
    width: 24px;
  }

  .collapse-btn {
    position: absolute;
    top: 8px;
    left: -1px;
    width: 24px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-right: none;
    border-radius: 4px 0 0 4px;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    z-index: 1;
    transition: color 0.15s;
  }

  .collapse-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface);
  }

  .panel-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }

  .panel-header {
    margin-bottom: 16px;
  }

  .category-badge {
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #fff;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
  }

  .node-label {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 6px 0;
  }

  .node-description {
    font-size: 11px;
    line-height: 1.5;
    color: var(--text-secondary);
    margin: 0;
  }

  .section {
    margin-bottom: 14px;
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 6px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border-color);
  }

  .ports-list,
  .params-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .port-item,
  .param-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
  }

  .port-direction {
    font-size: 9px;
    font-weight: 700;
    color: var(--text-muted);
    width: 24px;
  }

  .port-name {
    flex: 1;
    color: var(--text-secondary);
  }

  .port-type {
    font-size: 10px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    padding: 1px 5px;
    border-radius: 3px;
  }

  .param-name {
    flex: 1;
    color: var(--text-secondary);
  }

  .param-value {
    color: var(--text-primary);
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 11px;
  }
</style>
