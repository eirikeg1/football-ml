<script lang="ts">
  import type { NodeInstance } from "../../lib/types";
  import type { TableSelectorConfig, SqliteSourceConfig, CsvSourceConfig } from "../../lib/detail-types";
  import { graphState, updateDetailConfig } from "../../lib/state.svelte";

  interface Props {
    node: NodeInstance;
  }

  let { node }: Props = $props();

  let config = $derived<TableSelectorConfig>({
    selectedTable: "",
    columns: [],
    ...(node.detailConfig as Partial<TableSelectorConfig> | undefined),
  });

  // Resolve upstream data source config by following the input connection
  let upstreamConfig = $derived.by(() => {
    const conn = graphState.connections.find(
      (c) => c.toNode === node.instanceId && c.toPort === "dataset"
    );
    if (!conn) return null;
    const upstream = graphState.nodes.find((n) => n.instanceId === conn.fromNode);
    return upstream?.detailConfig as (SqliteSourceConfig | CsvSourceConfig) | null;
  });

  let availableTables = $derived.by(() => {
    if (!upstreamConfig) return [];
    if ("tables" in upstreamConfig && Array.isArray(upstreamConfig.tables)) {
      return upstreamConfig.tables
        .filter((t: { included: boolean }) => t.included)
        .map((t: { name: string }) => t.name);
    }
    if ("files" in upstreamConfig && Array.isArray(upstreamConfig.files)) {
      return upstreamConfig.files
        .filter((f: { included: boolean }) => f.included)
        .map((f: { filename: string }) => f.filename);
    }
    return [];
  });

  let availableColumns = $derived.by(() => {
    if (!upstreamConfig || !config.selectedTable) return [];
    if ("tables" in upstreamConfig && Array.isArray(upstreamConfig.tables)) {
      const table = upstreamConfig.tables.find(
        (t: { name: string }) => t.name === config.selectedTable
      );
      if (table && "columns" in table) {
        return table.columns
          .filter((c: { included: boolean }) => c.included)
          .map((c: { name: string }) => c.name);
      }
    }
    if ("files" in upstreamConfig && Array.isArray(upstreamConfig.files)) {
      const file = upstreamConfig.files.find(
        (f: { filename: string }) => f.filename === config.selectedTable
      );
      if (file) {
        return file.columns
          .filter((c: { included: boolean }) => c.included)
          .map((c: { name: string }) => c.name);
      }
    }
    return [];
  });

  function save(updates: Partial<TableSelectorConfig>) {
    updateDetailConfig(node.instanceId, { ...config, ...updates });
  }

  function selectTable(tableName: string) {
    save({ selectedTable: tableName, columns: [] });
  }

  function toggleColumn(colName: string) {
    const cols = config.columns.includes(colName)
      ? config.columns.filter((c) => c !== colName)
      : [...config.columns, colName];
    save({ columns: cols });
  }

  function selectAllColumns() {
    save({ columns: [...availableColumns] });
  }

  function deselectAllColumns() {
    save({ columns: [] });
  }
</script>

<div class="table-selector-panel">
  {#if !upstreamConfig}
    <div class="section">
      <p class="empty-hint">Connect a data source to the <strong>dataset</strong> input to configure table selection.</p>
    </div>
  {:else if availableTables.length === 0}
    <div class="section">
      <p class="empty-hint">No tables available. Import a schema in the upstream data source first.</p>
    </div>
  {:else}
    <!-- Table selection -->
    <div class="section">
      <div class="section-title">Select Table</div>
      <div class="table-list">
        {#each availableTables as tableName}
          <button
            class="table-option"
            class:active={config.selectedTable === tableName}
            onclick={() => selectTable(tableName)}
          >
            {tableName}
          </button>
        {/each}
      </div>
    </div>

    <!-- Column selection -->
    {#if config.selectedTable && availableColumns.length > 0}
      <div class="section">
        <div class="section-title">
          Columns ({config.columns.length}/{availableColumns.length})
          <span class="select-actions">
            <button class="link-btn" onclick={selectAllColumns}>All</button>
            <button class="link-btn" onclick={deselectAllColumns}>None</button>
          </span>
        </div>
        <div class="columns-list">
          {#each availableColumns as col}
            <label class="col-toggle">
              <input
                type="checkbox"
                checked={config.columns.includes(col)}
                onchange={() => toggleColumn(col)}
              />
              <span class="col-name">{col}</span>
            </label>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .table-selector-panel {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .section {
    margin-bottom: 12px;
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
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .empty-hint {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.6;
    text-align: center;
    padding: 12px;
  }

  .empty-hint strong {
    color: var(--text-secondary);
  }

  .table-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .table-option {
    text-align: left;
    font-size: 11px;
    padding: 5px 10px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 5px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.12s, border-color 0.12s;
  }

  .table-option:hover {
    background: var(--bg-surface);
    border-color: var(--border-active);
    color: var(--text-primary);
  }

  .table-option.active {
    background: rgba(74, 158, 255, 0.1);
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .select-actions {
    display: flex;
    gap: 6px;
  }

  .link-btn {
    font-size: 9px;
    background: none;
    border: none;
    color: var(--accent);
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
  }

  .link-btn:hover {
    color: var(--accent-hover);
  }

  .columns-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .col-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    padding: 2px 0;
  }

  .col-toggle input {
    flex-shrink: 0;
  }

  .col-name {
    font-size: 10px;
    color: var(--text-secondary);
  }
</style>
