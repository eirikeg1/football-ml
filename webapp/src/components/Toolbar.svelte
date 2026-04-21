<script lang="ts">
  import { clearGraph, graphState } from "../lib/state.svelte";
  import { exportYaml } from "../lib/yaml-export";
  import { importYaml } from "../lib/yaml-import";

  interface Props {
    activeView: "design" | "training";
    onViewChange: (view: "design" | "training") => void;
  }

  let { activeView, onViewChange }: Props = $props();

  function handleExport() {
    const yaml = exportYaml(graphState.nodes, graphState.connections);
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pipeline.yaml";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImport() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".yaml,.yml";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const text = await file.text();
      importYaml(text);
    };
    input.click();
  }

  function handleClear() {
    clearGraph();
  }
</script>

<div class="toolbar">
  <div class="toolbar-left">
    <div class="toolbar-title">football-ml</div>
    <div class="view-tabs">
      <button
        class="view-tab"
        class:active={activeView === "design"}
        onclick={() => onViewChange("design")}
      >Design</button>
      <button
        class="view-tab"
        class:active={activeView === "training"}
        onclick={() => onViewChange("training")}
      >Training</button>
    </div>
  </div>
  <div class="toolbar-actions">
    {#if activeView === "design"}
      <button onclick={handleImport}>Import YAML</button>
      <button onclick={handleExport}>Export YAML</button>
      <button onclick={handleClear}>Clear</button>
    {/if}
  </div>
</div>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: var(--toolbar-height);
    padding: 0 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .toolbar-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }

  .view-tabs {
    display: flex;
    gap: 2px;
    background: var(--bg-primary);
    border-radius: 6px;
    padding: 2px;
  }

  .view-tab {
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 500;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .view-tab:hover {
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.04);
  }

  .view-tab.active {
    background: var(--bg-surface);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  .toolbar-actions {
    display: flex;
    gap: 8px;
  }
</style>
