<script lang="ts">
  import type { NodeInstance } from "../../lib/types";
  import type { CsvSourceConfig, CsvFileEntry, ColumnSelection, Relationship } from "../../lib/detail-types";
  import { updateDetailConfig } from "../../lib/state.svelte";
  import RelationshipEditor from "./RelationshipEditor.svelte";

  interface Props {
    node: NodeInstance;
  }

  let { node }: Props = $props();

  let config = $derived<CsvSourceConfig>({
    directoryPath: "",
    files: [],
    relationships: [],
    ...(node.detailConfig as Partial<CsvSourceConfig> | undefined),
  });

  let expandedFiles = $state<Record<string, boolean>>({});

  function save(updates: Partial<CsvSourceConfig>) {
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
        const files: CsvFileEntry[] = (schema.tables ?? []).map(
          (t: { name: string; columns: { name: string; data_type: string }[] }) => ({
            filename: t.name,
            included: true,
            delimiter: ",",
            hasHeader: true,
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
            id: `rel_${i}`,
            fromTable: r.from_table,
            fromColumn: r.from_column,
            toTable: r.to_table,
            toColumn: r.to_column,
            type: (r.rel_type as Relationship["type"]) ?? "many_to_one",
            autoDetected: false,
          })
        );
        save({ files, relationships });
      } catch (err) {
        console.error("Failed to parse schema JSON:", err);
      }
    };
    reader.readAsText(file);
  }

  function toggleFile(filename: string) {
    const files = config.files.map((f) =>
      f.filename === filename ? { ...f, included: !f.included } : f
    );
    save({ files });
  }

  function toggleColumn(filename: string, colName: string) {
    const files = config.files.map((f) => {
      if (f.filename !== filename) return f;
      return {
        ...f,
        columns: f.columns.map((c) =>
          c.name === colName ? { ...c, included: !c.included } : c
        ),
      };
    });
    save({ files });
  }

  function setColumnRole(filename: string, colName: string, role: ColumnSelection["role"]) {
    const files = config.files.map((f) => {
      if (f.filename !== filename) return f;
      return {
        ...f,
        columns: f.columns.map((c) =>
          c.name === colName ? { ...c, role } : c
        ),
      };
    });
    save({ files });
  }

  function updateDelimiter(filename: string, delimiter: string) {
    const files = config.files.map((f) =>
      f.filename === filename ? { ...f, delimiter } : f
    );
    save({ files });
  }

  function toggleExpand(filename: string) {
    expandedFiles[filename] = !expandedFiles[filename];
  }

  function handleRelUpdate(relationships: Relationship[]) {
    save({ relationships });
  }

  // For RelationshipEditor, convert files to tables format
  let tablesForRels = $derived(
    config.files.map((f) => ({ name: f.filename, columns: f.columns }))
  );
</script>

<div class="csv-panel">
  <!-- Schema import -->
  <div class="section">
    <div class="section-title">Schema</div>
    <p class="section-hint">
      Run <code>python -m football_ml.datasource introspect &lt;dir&gt; --type csv</code> and import the JSON.
    </p>
    <label class="import-btn">
      Import Schema JSON
      <input type="file" accept=".json" onchange={handleSchemaImport} style="display: none;" />
    </label>
  </div>

  <!-- Files -->
  {#if config.files.length > 0}
    <div class="section">
      <div class="section-title">Files ({config.files.filter(f => f.included).length}/{config.files.length})</div>
      <div class="files-list">
        {#each config.files as file}
          <div class="file-entry">
            <div class="file-header">
              <label class="file-toggle">
                <input
                  type="checkbox"
                  checked={file.included}
                  onchange={() => toggleFile(file.filename)}
                />
                <span class="file-name">{file.filename}</span>
              </label>
              <span class="file-delim" title="Delimiter">
                <select
                  value={file.delimiter}
                  onchange={(e) =>
                    updateDelimiter(file.filename, (e.target as HTMLSelectElement).value)}
                >
                  <option value=",">,</option>
                  <option value=";">;</option>
                  <option value="\t">tab</option>
                  <option value="|">|</option>
                </select>
              </span>
              <button class="expand-btn" onclick={() => toggleExpand(file.filename)}>
                <svg width="8" height="8" viewBox="0 0 10 10">
                  <path
                    d={expandedFiles[file.filename] ? "M1.5 3 L5 7 L8.5 3" : "M3 1.5 L7 5 L3 8.5"}
                    fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                  />
                </svg>
              </button>
            </div>
            {#if expandedFiles[file.filename]}
              <div class="columns-list">
                {#each file.columns as col}
                  <div class="column-row">
                    <label class="col-toggle">
                      <input
                        type="checkbox"
                        checked={col.included}
                        onchange={() => toggleColumn(file.filename, col.name)}
                      />
                      <span class="col-name">{col.name}</span>
                    </label>
                    <span class="col-type">{col.dataType}</span>
                    <select
                      class="col-role"
                      value={col.role}
                      onchange={(e) =>
                        setColumnRole(file.filename, col.name, (e.target as HTMLSelectElement).value as ColumnSelection["role"])}
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
      <p class="section-hint">CSV files have no automatic FK detection. Define relationships manually.</p>
      <RelationshipEditor
        relationships={config.relationships}
        tables={tablesForRels}
        onupdate={handleRelUpdate}
      />
    </div>
  {/if}
</div>

<style>
  .csv-panel {
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

  .files-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .file-entry {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow: hidden;
  }

  .file-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
  }

  .file-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    cursor: pointer;
    min-width: 0;
  }

  .file-toggle input {
    flex-shrink: 0;
  }

  .file-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-delim select {
    font-size: 9px;
    padding: 0 2px;
    width: 36px;
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
