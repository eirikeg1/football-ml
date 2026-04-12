<script lang="ts">
  import type { NodeInstance } from "../../lib/types";
  import type { SqliteSourceConfig, TableSelection, ColumnSelection, Relationship } from "../../lib/detail-types";
  import { updateDetailConfig } from "../../lib/state.svelte";
  import RelationshipEditor from "./RelationshipEditor.svelte";

  interface Props {
    node: NodeInstance;
  }

  let { node }: Props = $props();

  let config = $derived<SqliteSourceConfig>({
    dbPath: "",
    tables: [],
    relationships: [],
    ...(node.detailConfig as Partial<SqliteSourceConfig> | undefined),
  });

  let expandedTables = $state<Record<string, boolean>>({});

  function save(updates: Partial<SqliteSourceConfig>) {
    updateDetailConfig(node.instanceId, { ...config, ...updates });
  }

  function handleSchemaImport(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const schema = JSON.parse(reader.result as string);
        const tables: TableSelection[] = (schema.tables ?? []).map(
          (t: { name: string; columns: { name: string; data_type: string }[] }) => ({
            name: t.name,
            included: true,
            columns: (t.columns ?? []).map(
              (c: { name: string; data_type: string }) => ({
                name: c.name,
                dataType: c.data_type ?? "text",
                included: true,
                role: c.name === "id" || c.name.endsWith("_id") ? "key" as const : "feature" as const,
              })
            ),
          })
        );
        const relationships: Relationship[] = (schema.relationships ?? []).map(
          (r: { from_table: string; from_column: string; to_table: string; to_column: string; rel_type?: string }, i: number) => ({
            id: `fk_${i}`,
            fromTable: r.from_table,
            fromColumn: r.from_column,
            toTable: r.to_table,
            toColumn: r.to_column,
            type: (r.rel_type as Relationship["type"]) ?? "many_to_one",
            autoDetected: true,
          })
        );
        save({ tables, relationships });
      } catch (err) {
        console.error("Failed to parse schema JSON:", err);
      }
    };
    reader.readAsText(file);
  }

  function toggleTable(tableName: string) {
    const tables = config.tables.map((t) =>
      t.name === tableName ? { ...t, included: !t.included } : t
    );
    save({ tables });
  }

  function toggleColumn(tableName: string, colName: string) {
    const tables = config.tables.map((t) => {
      if (t.name !== tableName) return t;
      return {
        ...t,
        columns: t.columns.map((c) =>
          c.name === colName ? { ...c, included: !c.included } : c
        ),
      };
    });
    save({ tables });
  }

  function setColumnRole(tableName: string, colName: string, role: ColumnSelection["role"]) {
    const tables = config.tables.map((t) => {
      if (t.name !== tableName) return t;
      return {
        ...t,
        columns: t.columns.map((c) =>
          c.name === colName ? { ...c, role } : c
        ),
      };
    });
    save({ tables });
  }

  function toggleExpand(tableName: string) {
    expandedTables[tableName] = !expandedTables[tableName];
  }

  function handleRelUpdate(relationships: Relationship[]) {
    save({ relationships });
  }
</script>

<div class="sqlite-panel">
  <!-- Connection -->
  <div class="section">
    <div class="section-title">Schema</div>
    <p class="section-hint">
      Run <code>python -m football_ml.datasource introspect &lt;db_path&gt;</code> and import the JSON output.
    </p>
    <label class="import-btn">
      Import Schema JSON
      <input type="file" accept=".json" onchange={handleSchemaImport} style="display: none;" />
    </label>
  </div>

  <!-- Tables -->
  {#if config.tables.length > 0}
    <div class="section">
      <div class="section-title">Tables ({config.tables.filter(t => t.included).length}/{config.tables.length})</div>
      <div class="tables-list">
        {#each config.tables as table}
          <div class="table-entry">
            <div class="table-header">
              <label class="table-toggle">
                <input
                  type="checkbox"
                  checked={table.included}
                  onchange={() => toggleTable(table.name)}
                />
                <span class="table-name">{table.name}</span>
              </label>
              <span class="col-count">{table.columns.length} cols</span>
              <button class="expand-btn" onclick={() => toggleExpand(table.name)}>
                <svg width="8" height="8" viewBox="0 0 10 10">
                  <path
                    d={expandedTables[table.name] ? "M1.5 3 L5 7 L8.5 3" : "M3 1.5 L7 5 L3 8.5"}
                    fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                  />
                </svg>
              </button>
            </div>
            {#if expandedTables[table.name]}
              <div class="columns-list">
                {#each table.columns as col}
                  <div class="column-row">
                    <label class="col-toggle">
                      <input
                        type="checkbox"
                        checked={col.included}
                        onchange={() => toggleColumn(table.name, col.name)}
                      />
                      <span class="col-name">{col.name}</span>
                    </label>
                    <span class="col-type">{col.dataType}</span>
                    <select
                      class="col-role"
                      value={col.role}
                      onchange={(e) =>
                        setColumnRole(table.name, col.name, (e.target as HTMLSelectElement).value as ColumnSelection["role"])}
                    >
                      <option value="feature">feature</option>
                      <option value="label">label</option>
                      <option value="key">key</option>
                      <option value="ignore">ignore</option>
                    </select>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <!-- Relationships -->
    <div class="section">
      <div class="section-title">Relationships ({config.relationships.length})</div>
      <RelationshipEditor
        relationships={config.relationships}
        tables={config.tables}
        onupdate={handleRelUpdate}
      />
    </div>
  {/if}
</div>

<style>
  .sqlite-panel {
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
  }

  .section-hint {
    font-size: 10px;
    color: var(--text-muted);
    margin: 0 0 8px 0;
    line-height: 1.5;
  }

  .section-hint code {
    font-size: 9px;
    background: rgba(255, 255, 255, 0.06);
    padding: 1px 4px;
    border-radius: 3px;
    color: var(--text-secondary);
  }

  .import-btn {
    display: block;
    text-align: center;
    font-size: 11px;
    padding: 6px 12px;
    background: rgba(74, 158, 255, 0.08);
    border: 1px dashed var(--accent);
    border-radius: 6px;
    color: var(--accent);
    cursor: pointer;
    transition: background 0.15s;
  }

  .import-btn:hover {
    background: rgba(74, 158, 255, 0.15);
  }

  .tables-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .table-entry {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow: hidden;
  }

  .table-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
  }

  .table-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    cursor: pointer;
    min-width: 0;
  }

  .table-toggle input {
    flex-shrink: 0;
  }

  .table-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .col-count {
    font-size: 9px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .expand-btn {
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    flex-shrink: 0;
  }

  .expand-btn:hover {
    color: var(--text-primary);
  }

  .columns-list {
    border-top: 1px solid var(--border-color);
    padding: 4px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .column-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .col-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    flex: 1;
    cursor: pointer;
    min-width: 0;
  }

  .col-toggle input {
    flex-shrink: 0;
  }

  .col-name {
    font-size: 10px;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .col-type {
    font-size: 9px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    padding: 0 4px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .col-role {
    font-size: 9px;
    padding: 0 2px;
    flex-shrink: 0;
    width: 60px;
  }
</style>
