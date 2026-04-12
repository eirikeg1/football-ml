<script lang="ts">
  import type { Relationship, TableSelection } from "../../lib/detail-types";

  interface Props {
    relationships: Relationship[];
    tables: TableSelection[] | { name: string }[];
    onupdate: (relationships: Relationship[]) => void;
  }

  let { relationships, tables, onupdate }: Props = $props();

  let nextId = $state(1);

  function allColumns(tableName: string): string[] {
    const table = tables.find((t) => t.name === tableName);
    if (!table || !("columns" in table)) return [];
    return table.columns.map((c) => c.name);
  }

  function tableNames(): string[] {
    return tables.map((t) => t.name);
  }

  function addRelationship() {
    const names = tableNames();
    const newRel: Relationship = {
      id: `rel_${Date.now()}_${nextId++}`,
      fromTable: names[0] ?? "",
      fromColumn: "",
      toTable: names[0] ?? "",
      toColumn: "",
      type: "many_to_one",
      autoDetected: false,
    };
    onupdate([...relationships, newRel]);
  }

  function removeRelationship(id: string) {
    onupdate(relationships.filter((r) => r.id !== id));
  }

  function updateField(
    id: string,
    field: keyof Relationship,
    value: string
  ) {
    onupdate(
      relationships.map((r) =>
        r.id === id ? { ...r, [field]: value } : r
      )
    );
  }
</script>

<div class="rel-editor">
  {#each relationships as rel}
    <div class="rel-row" class:auto={rel.autoDetected}>
      <div class="rel-mapping">
        <div class="rel-side">
          <select
            value={rel.fromTable}
            onchange={(e) =>
              updateField(rel.id, "fromTable", (e.target as HTMLSelectElement).value)}
          >
            {#each tableNames() as t}
              <option value={t}>{t}</option>
            {/each}
          </select>
          <select
            value={rel.fromColumn}
            onchange={(e) =>
              updateField(rel.id, "fromColumn", (e.target as HTMLSelectElement).value)}
          >
            <option value="">-- column --</option>
            {#each allColumns(rel.fromTable) as col}
              <option value={col}>{col}</option>
            {/each}
          </select>
        </div>
        <span class="rel-arrow">&#8594;</span>
        <div class="rel-side">
          <select
            value={rel.toTable}
            onchange={(e) =>
              updateField(rel.id, "toTable", (e.target as HTMLSelectElement).value)}
          >
            {#each tableNames() as t}
              <option value={t}>{t}</option>
            {/each}
          </select>
          <select
            value={rel.toColumn}
            onchange={(e) =>
              updateField(rel.id, "toColumn", (e.target as HTMLSelectElement).value)}
          >
            <option value="">-- column --</option>
            {#each allColumns(rel.toTable) as col}
              <option value={col}>{col}</option>
            {/each}
          </select>
        </div>
      </div>
      <div class="rel-meta">
        <select
          class="rel-type-select"
          value={rel.type}
          onchange={(e) =>
            updateField(rel.id, "type", (e.target as HTMLSelectElement).value)}
        >
          <option value="many_to_one">many:1</option>
          <option value="one_to_many">1:many</option>
          <option value="many_to_many">many:many</option>
        </select>
        {#if rel.autoDetected}
          <span class="auto-badge">FK</span>
        {/if}
        <button class="rel-remove" onclick={() => removeRelationship(rel.id)} title="Remove relationship">
          <svg width="10" height="10" viewBox="0 0 10 10">
            <path d="M2 2 L8 8 M8 2 L2 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
  {/each}

  <button class="add-rel-btn" onclick={addRelationship}>+ Add Relationship</button>
</div>

<style>
  .rel-editor {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .rel-row {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 6px 8px;
  }

  .rel-row.auto {
    border-left: 2px solid var(--accent);
  }

  .rel-mapping {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 4px;
  }

  .rel-side {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0;
  }

  .rel-side select {
    width: 100%;
    font-size: 10px;
    padding: 2px 3px;
  }

  .rel-arrow {
    color: var(--text-muted);
    font-size: 12px;
    flex-shrink: 0;
    padding: 0 2px;
  }

  .rel-meta {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .rel-type-select {
    font-size: 10px;
    padding: 1px 3px;
  }

  .auto-badge {
    font-size: 8px;
    font-weight: 700;
    color: var(--accent);
    background: rgba(74, 158, 255, 0.1);
    padding: 1px 5px;
    border-radius: 3px;
  }

  .rel-remove {
    margin-left: auto;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    border-radius: 3px;
  }

  .rel-remove:hover {
    color: #e05c6c;
    background: rgba(224, 92, 108, 0.1);
  }

  .add-rel-btn {
    font-size: 11px;
    padding: 5px 10px;
    text-align: center;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.03);
    border: 1px dashed var(--border-color);
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }

  .add-rel-btn:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: var(--border-active);
    color: var(--text-primary);
  }
</style>
