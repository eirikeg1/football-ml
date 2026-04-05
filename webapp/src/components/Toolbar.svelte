<script lang="ts">
  import { clearGraph, graphState } from "../lib/state.svelte";
  import { exportYaml } from "../lib/yaml-export";
  import { importYaml } from "../lib/yaml-import";

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
  <div class="toolbar-title">football-ml Pipeline Editor</div>
  <div class="toolbar-actions">
    <button onclick={handleImport}>Import YAML</button>
    <button onclick={handleExport}>Export YAML</button>
    <button onclick={handleClear}>Clear</button>
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

  .toolbar-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }

  .toolbar-actions {
    display: flex;
    gap: 8px;
  }
</style>
