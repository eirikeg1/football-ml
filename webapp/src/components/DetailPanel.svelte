<script lang="ts">
  import { graphState, getSelectedNode } from "../lib/state.svelte";
  import { getNodeDef } from "../lib/registry";
  import { validateNode } from "../lib/validation";
  import { CATEGORY_COLORS, CATEGORY_LABELS } from "../lib/types";
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
  let categoryLabel = $derived(def ? CATEGORY_LABELS[def.category] : "");

  let report = $derived(
    selectedNode ? validateNode(selectedNode.instanceId, graphState) : null
  );

  function toggleCollapse() {
    collapsed = !collapsed;
  }

  function statusSymbol(status: string): string {
    if (status === "ok") return "✓";
    if (status === "warning") return "⚠";
    if (status === "error") return "✗";
    return "○";
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

        <!-- Node-level status banner -->
        {#if report && report.worstSeverity !== "ok"}
          <div class="status-banner" class:error={report.worstSeverity === "error"} class:warning={report.worstSeverity === "warning"}>
            <span class="banner-icon">{report.worstSeverity === "error" ? "✗" : "⚠"}</span>
            <span class="banner-text">
              {report.worstSeverity === "error" ? "Connection errors on this node" : "Connection warnings on this node"}
            </span>
          </div>
        {/if}

        <!-- Connection Requirements -->
        {#if report && (report.inputs.length > 0 || report.outputs.length > 0)}
          <div class="section">
            <div class="section-title">Connection Requirements</div>

            {#each report.inputs as input}
              <div class="req-row" class:error={input.status === "error"} class:warning={input.status === "warning"} class:missing={input.status === "missing"}>
                <div class="req-head">
                  <span class="req-status" title={input.status}>{statusSymbol(input.status)}</span>
                  <span class="req-name">IN · {input.portName}</span>
                  <span class="req-chip" title="data type">{input.dataType}</span>
                  <span class="req-chip subtle" title="shape">{input.shape}</span>
                </div>

                <div class="req-expected">
                  expects
                  <span class="mono">{input.shape}</span>
                  of
                  <span class="mono">{input.dataType}</span>
                  {#if input.widthParam}
                    , width
                    <span class="mono">{input.widthParam}{input.expectedWidth !== undefined ? ` = ${input.expectedWidth}` : " (unset)"}</span>
                  {/if}
                  {#if input.multi}
                    <span class="req-chip subtle" title="multi-input semantics">multi · {input.multiSemantics}</span>
                  {/if}
                  {#if !input.required}
                    <span class="req-chip subtle">optional</span>
                  {/if}
                </div>

                {#if input.connections.length > 0}
                  {#each input.connections as c}
                    <div class="req-connection">
                      ← <strong>{c.fromNodeLabel}</strong>.{c.fromPort}
                      {#if c.actualWidth !== undefined}
                        <span class="mono dim">w={c.actualWidth}</span>
                      {/if}
                      {#if c.actualShape}
                        <span class="mono dim">{c.actualShape}</span>
                      {/if}
                      {#if c.issues.length > 0}
                        <ul class="req-issues">
                          {#each c.issues as issue}
                            <li class:err={issue.severity === "error"} class:warn={issue.severity === "warning"}>
                              {issue.message}
                              {#if issue.detail}
                                <div class="req-issue-detail">{issue.detail}</div>
                              {/if}
                            </li>
                          {/each}
                        </ul>
                      {/if}
                    </div>
                  {/each}
                {/if}

                {#if input.issues.length > 0}
                  <ul class="req-issues">
                    {#each input.issues as issue}
                      <li class:err={issue.severity === "error"} class:warn={issue.severity === "warning"}>
                        {issue.message}
                        {#if issue.detail}
                          <div class="req-issue-detail">{issue.detail}</div>
                        {/if}
                      </li>
                    {/each}
                  </ul>
                {/if}
              </div>
            {/each}

            {#each report.outputs as output}
              <div class="req-row out">
                <div class="req-head">
                  <span class="req-status out-dot">→</span>
                  <span class="req-name">OUT · {output.portName}</span>
                  <span class="req-chip" title="data type">{output.dataType}</span>
                  <span class="req-chip subtle" title="shape">{output.shape}</span>
                </div>
                <div class="req-expected">
                  provides <span class="mono">{output.shape}</span> of <span class="mono">{output.dataType}</span>
                  {#if output.widthParam}
                    , width <span class="mono">{output.widthParam}{output.width !== undefined ? ` = ${output.width}` : " (unset)"}</span>
                  {/if}
                </div>
                {#if output.consumers.length > 0}
                  <div class="req-consumers">
                    feeds: {output.consumers.map((c) => `${c.toNodeLabel}.${c.toPort}`).join(", ")}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}

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
    margin-bottom: 12px;
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

  .status-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    padding: 8px 10px;
    border-radius: 6px;
    margin-bottom: 12px;
    border: 1px solid var(--border-color);
    background: rgba(255, 255, 255, 0.02);
  }

  .status-banner.error {
    border-color: var(--error);
    background: rgba(229, 72, 77, 0.1);
    color: var(--error-strong);
  }

  .status-banner.warning {
    border-color: var(--warning);
    background: rgba(245, 166, 35, 0.1);
    color: var(--warning-strong);
  }

  .banner-icon {
    font-weight: 700;
    font-size: 13px;
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

  .params-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .param-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
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

  /* Connection requirements */
  .req-row {
    padding: 6px 8px;
    border: 1px solid var(--border-color);
    border-radius: 5px;
    margin-bottom: 6px;
    background: rgba(255, 255, 255, 0.015);
  }

  .req-row.error {
    border-color: var(--error);
    background: rgba(229, 72, 77, 0.06);
  }

  .req-row.warning {
    border-color: var(--warning);
    background: rgba(245, 166, 35, 0.06);
  }

  .req-row.missing {
    border-color: var(--warning);
    border-style: dashed;
    background: rgba(245, 166, 35, 0.04);
  }

  .req-row.out {
    border-style: dashed;
    border-color: var(--border-color);
    background: rgba(255, 255, 255, 0.01);
  }

  .req-head {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }

  .req-status {
    display: inline-flex;
    width: 14px;
    height: 14px;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
  }

  .req-row.error .req-status {
    color: var(--error);
  }

  .req-row.warning .req-status,
  .req-row.missing .req-status {
    color: var(--warning);
  }

  .req-row:not(.error):not(.warning):not(.missing) .req-status {
    color: #59c97a;
  }

  .out-dot {
    color: var(--text-muted) !important;
  }

  .req-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    flex: 1;
  }

  .req-chip {
    font-size: 9.5px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    padding: 1px 6px;
    border-radius: 3px;
  }

  .req-chip.subtle {
    background: transparent;
    border: 1px solid var(--border-color);
  }

  .req-expected {
    font-size: 10.5px;
    color: var(--text-secondary);
    line-height: 1.5;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 3px;
  }

  .req-connection {
    margin-top: 4px;
    padding: 4px 6px;
    font-size: 10.5px;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.02);
    border-radius: 3px;
  }

  .req-consumers {
    font-size: 10.5px;
    color: var(--text-muted);
    margin-top: 3px;
  }

  .req-issues {
    list-style: none;
    margin: 4px 0 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .req-issues li {
    font-size: 10.5px;
    padding: 3px 6px;
    border-left: 2px solid var(--border-color);
    background: rgba(255, 255, 255, 0.02);
    color: var(--text-secondary);
  }

  .req-issues li.err {
    border-left-color: var(--error);
    background: rgba(229, 72, 77, 0.08);
  }

  .req-issues li.warn {
    border-left-color: var(--warning);
    background: rgba(245, 166, 35, 0.08);
  }

  .req-issue-detail {
    margin-top: 2px;
    color: var(--text-muted);
    font-size: 10px;
    line-height: 1.5;
  }

  .mono {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 10px;
    color: var(--text-primary);
  }

  .mono.dim {
    color: var(--text-muted);
  }
</style>
