<script lang="ts">
  import type { NodeInstance } from "../../lib/types";
  import type {
    MaterializationConfig,
    FlattenOptions,
    GraphOptions,
    SqliteSourceConfig,
    CsvSourceConfig,
    Relationship,
  } from "../../lib/detail-types";
  import { graphState, updateDetailConfig } from "../../lib/state.svelte";

  interface Props {
    node: NodeInstance;
  }

  let { node }: Props = $props();

  let config = $derived<MaterializationConfig>({
    strategy: (node.params.strategy as MaterializationConfig["strategy"]) ?? "flatten",
    flattenOptions: { joinOrder: [], joinType: "inner" },
    graphOptions: { nodeTypes: [], edgeTypes: [] },
    ...(node.detailConfig as Partial<MaterializationConfig> | undefined),
  });

  // Resolve upstream data source
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

  let availableRelationships = $derived.by(() => {
    if (!upstreamConfig) return [];
    return (upstreamConfig.relationships ?? []) as Relationship[];
  });

  function save(updates: Partial<MaterializationConfig>) {
    updateDetailConfig(node.instanceId, { ...config, ...updates });
  }

  // Flatten helpers
  function setJoinType(joinType: FlattenOptions["joinType"]) {
    save({
      flattenOptions: { ...config.flattenOptions!, joinType },
    });
  }

  function moveInJoinOrder(table: string, direction: -1 | 1) {
    const order = [...(config.flattenOptions?.joinOrder ?? [])];
    const idx = order.indexOf(table);
    if (idx === -1) return;
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= order.length) return;
    [order[idx], order[newIdx]] = [order[newIdx], order[idx]];
    save({
      flattenOptions: { ...config.flattenOptions!, joinOrder: order },
    });
  }

  function initJoinOrder() {
    save({
      flattenOptions: {
        ...config.flattenOptions!,
        joinOrder: [...availableTables],
      },
    });
  }

  // Graph helpers
  function toggleGraphNodeType(table: string) {
    const existing = config.graphOptions?.nodeTypes ?? [];
    const has = existing.some((n) => n.table === table);
    const nodeTypes = has
      ? existing.filter((n) => n.table !== table)
      : [...existing, { table, features: [] }];
    save({ graphOptions: { ...config.graphOptions!, nodeTypes } });
  }

  function toggleGraphEdgeType(relId: string) {
    const existing = config.graphOptions?.edgeTypes ?? [];
    const has = existing.some((e) => e.relationship === relId);
    const edgeTypes = has
      ? existing.filter((e) => e.relationship !== relId)
      : [...existing, { relationship: relId, directed: true }];
    save({ graphOptions: { ...config.graphOptions!, edgeTypes } });
  }
</script>

<div class="mat-panel">
  {#if !upstreamConfig}
    <div class="section">
      <p class="empty-hint">Connect a data source to the <strong>dataset</strong> input to configure materialization.</p>
    </div>
  {:else}
    <!-- Strategy-specific config -->
    {#if config.strategy === "flatten"}
      <div class="section">
        <div class="section-title">Flatten Configuration</div>

        <div class="field">
          <label class="field-label">Join Type</label>
          <select
            value={config.flattenOptions?.joinType ?? "inner"}
            onchange={(e) => setJoinType((e.target as HTMLSelectElement).value as FlattenOptions["joinType"])}
          >
            <option value="inner">Inner Join</option>
            <option value="left">Left Join</option>
            <option value="outer">Outer Join</option>
          </select>
        </div>

        <div class="field">
          <label class="field-label">Join Order</label>
          {#if (config.flattenOptions?.joinOrder?.length ?? 0) === 0}
            <button class="init-btn" onclick={initJoinOrder}>Initialize from tables</button>
          {:else}
            <div class="join-order">
              {#each config.flattenOptions?.joinOrder ?? [] as table, i}
                <div class="join-item">
                  <span class="join-index">{i + 1}</span>
                  <span class="join-table">{table}</span>
                  <div class="join-arrows">
                    <button
                      class="arrow-btn"
                      disabled={i === 0}
                      onclick={() => moveInJoinOrder(table, -1)}
                      title="Move up"
                    >&#9650;</button>
                    <button
                      class="arrow-btn"
                      disabled={i === (config.flattenOptions?.joinOrder?.length ?? 0) - 1}
                      onclick={() => moveInJoinOrder(table, 1)}
                      title="Move down"
                    >&#9660;</button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

    {:else if config.strategy === "heterogeneous_graph"}
      <div class="section">
        <div class="section-title">Graph Configuration</div>

        <div class="field">
          <label class="field-label">Node Types (tables as graph nodes)</label>
          <div class="check-list">
            {#each availableTables as table}
              <label class="check-item">
                <input
                  type="checkbox"
                  checked={(config.graphOptions?.nodeTypes ?? []).some(n => n.table === table)}
                  onchange={() => toggleGraphNodeType(table)}
                />
                <span>{table}</span>
              </label>
            {/each}
          </div>
        </div>

        {#if availableRelationships.length > 0}
          <div class="field">
            <label class="field-label">Edge Types (relationships as edges)</label>
            <div class="check-list">
              {#each availableRelationships as rel}
                <label class="check-item">
                  <input
                    type="checkbox"
                    checked={(config.graphOptions?.edgeTypes ?? []).some(e => e.relationship === rel.id)}
                    onchange={() => toggleGraphEdgeType(rel.id)}
                  />
                  <span class="rel-label">{rel.fromTable}.{rel.fromColumn} &#8594; {rel.toTable}.{rel.toColumn}</span>
                </label>
              {/each}
            </div>
          </div>
        {/if}
      </div>

    {:else if config.strategy === "aligned"}
      <div class="section">
        <div class="section-title">Aligned Configuration</div>
        <p class="section-hint">
          Tables will be kept as separate tensors, aligned by their shared key columns (foreign keys).
          No additional configuration needed — alignment uses the relationships defined in the data source.
        </p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .mat-panel {
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
    line-height: 1.6;
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

  .field {
    margin-bottom: 10px;
  }

  .field-label {
    display: block;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .field select {
    width: 100%;
    font-size: 11px;
    padding: 4px 6px;
  }

  .init-btn {
    font-size: 10px;
    padding: 4px 10px;
    width: 100%;
    text-align: center;
    color: var(--accent);
    background: rgba(74, 158, 255, 0.08);
    border: 1px dashed var(--accent);
    border-radius: 5px;
    cursor: pointer;
  }

  .init-btn:hover {
    background: rgba(74, 158, 255, 0.15);
  }

  .join-order {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .join-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 6px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }

  .join-index {
    font-size: 9px;
    font-weight: 700;
    color: var(--text-muted);
    width: 14px;
    text-align: center;
  }

  .join-table {
    font-size: 11px;
    color: var(--text-primary);
    flex: 1;
  }

  .join-arrows {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .arrow-btn {
    font-size: 8px;
    padding: 0;
    width: 16px;
    height: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    line-height: 1;
  }

  .arrow-btn:hover:not(:disabled) {
    color: var(--text-primary);
  }

  .arrow-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .check-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .check-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 2px 0;
  }

  .check-item input {
    flex-shrink: 0;
  }

  .rel-label {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 9px;
  }
</style>
