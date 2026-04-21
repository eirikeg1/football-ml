<script lang="ts">
  import { graphState } from "../../lib/state.svelte";
  import { getNodeDef } from "../../lib/registry";
  import { trainingState, resetTraining } from "../../lib/training-state.svelte";
  import { exportYaml } from "../../lib/yaml-export";
  import {
    startTraining,
    stopTraining,
    pauseTraining,
  } from "../../lib/training-api";

  // Detect active heads from the graph
  let activeHeads = $derived(
    graphState.nodes
      .filter((n) => {
        const def = getNodeDef(n.defId);
        return def?.category === "heads";
      })
      .map((n) => n.defId)
  );

  let config = trainingState.config;
  let status = $derived(trainingState.status);
  let isTraining = $derived(status === "training" || status === "paused");

  async function handleStart() {
    // Update heads from graph
    config.heads = activeHeads.length > 0 ? activeHeads : ["match_outcome"];
    trainingState.config = config;

    resetTraining();
    trainingState.totalEpochs = config.epochs;

    const yaml = exportYaml(graphState.nodes, graphState.connections);
    const result = await startTraining(yaml, config);

    if (result.status === "error") {
      trainingState.status = "error";
    }
  }

  async function handleStop() {
    await stopTraining();
  }

  async function handlePause() {
    await pauseTraining();
  }
</script>

<div class="config-panel">
  <div class="panel-scroll">
    <!-- Pipeline Summary -->
    <div class="section">
      <div class="section-title">Pipeline</div>
      {#if activeHeads.length > 0}
        <div class="head-list">
          {#each activeHeads as head}
            <span class="head-badge">{head.replace("_", " ")}</span>
          {/each}
        </div>
      {:else}
        <p class="hint">No prediction heads in the graph. Add one in the Design view.</p>
      {/if}
    </div>

    <!-- Optimizer -->
    <div class="section">
      <div class="section-title">Optimizer</div>
      <div class="field">
        <label class="field-label">Type</label>
        <select bind:value={config.optimizer} disabled={isTraining}>
          <option value="adam">Adam</option>
          <option value="sgd">SGD</option>
          <option value="adamw">AdamW</option>
        </select>
      </div>
      <div class="field">
        <label class="field-label">Learning Rate</label>
        <input
          type="number"
          step="0.0001"
          min="0"
          bind:value={config.learning_rate}
          disabled={isTraining}
        />
      </div>
      <div class="field">
        <label class="field-label">Weight Decay</label>
        <input
          type="number"
          step="0.001"
          min="0"
          bind:value={config.weight_decay}
          disabled={isTraining}
        />
      </div>
    </div>

    <!-- Training -->
    <div class="section">
      <div class="section-title">Training</div>
      <div class="field">
        <label class="field-label">Epochs</label>
        <input
          type="number"
          min="1"
          bind:value={config.epochs}
          disabled={isTraining}
        />
      </div>
      <div class="field">
        <label class="field-label">Batch Size</label>
        <input
          type="number"
          min="1"
          bind:value={config.batch_size}
          disabled={isTraining}
        />
      </div>
      <div class="field">
        <label class="field-label">Validation Split</label>
        <div class="range-field">
          <input
            type="range"
            min="0"
            max="0.5"
            step="0.05"
            bind:value={config.val_split}
            disabled={isTraining}
          />
          <span class="range-value">{Math.round(config.val_split * 100)}%</span>
        </div>
      </div>
    </div>

    <!-- Early Stopping -->
    <div class="section">
      <div class="section-title">Early Stopping</div>
      <div class="field">
        <label class="field-label">Patience</label>
        <input
          type="number"
          min="0"
          bind:value={config.early_stopping_patience}
          disabled={isTraining}
        />
      </div>
      <p class="hint">Set to 0 to disable early stopping.</p>
    </div>

    <!-- LR Scheduler -->
    <div class="section">
      <div class="section-title">LR Scheduler</div>
      <div class="field">
        <label class="field-label">Type</label>
        <select bind:value={config.scheduler} disabled={isTraining}>
          <option value={null}>None</option>
          <option value="step">Step LR</option>
          <option value="cosine">Cosine Annealing</option>
          <option value="warmup">Linear Warmup</option>
        </select>
      </div>
    </div>

    <!-- Metrics -->
    <div class="section">
      <div class="section-title">Metrics</div>
      <div class="field">
        <label class="field-label">Track</label>
        <select bind:value={config.metrics[0]} disabled={isTraining}>
          <option value="accuracy">Accuracy</option>
          <option value="f1_macro">F1 (Macro)</option>
          <option value="f1_weighted">F1 (Weighted)</option>
          <option value="mae">MAE</option>
          <option value="mse">MSE</option>
        </select>
      </div>
    </div>
  </div>

  <!-- Action buttons -->
  <div class="actions">
    {#if status === "idle" || status === "completed" || status === "error"}
      <button class="btn-primary" onclick={handleStart} disabled={activeHeads.length === 0}>
        Start Training
      </button>
    {:else if status === "training"}
      <button class="btn-warning" onclick={handlePause}>Pause</button>
      <button class="btn-danger" onclick={handleStop}>Stop</button>
    {:else if status === "paused"}
      <button class="btn-primary" onclick={handlePause}>Resume</button>
      <button class="btn-danger" onclick={handleStop}>Stop</button>
    {/if}
  </div>
</div>

<style>
  .config-panel {
    width: 300px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .panel-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }

  .section {
    margin-bottom: 16px;
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border-color);
  }

  .field {
    margin-bottom: 8px;
  }

  .field-label {
    display: block;
    font-size: 11px;
    color: var(--text-secondary);
    margin-bottom: 3px;
  }

  .field input[type="number"],
  .field select {
    width: 100%;
    font-size: 12px;
    padding: 4px 8px;
  }

  .range-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .range-field input[type="range"] {
    flex: 1;
    accent-color: var(--accent);
  }

  .range-value {
    font-size: 11px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--text-primary);
    min-width: 32px;
    text-align: right;
  }

  .hint {
    font-size: 10px;
    color: var(--text-muted);
    margin: 2px 0 0 0;
    line-height: 1.4;
  }

  .head-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .head-badge {
    font-size: 10px;
    font-weight: 600;
    color: var(--color-heads);
    background: rgba(224, 92, 108, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: capitalize;
  }

  .actions {
    padding: 12px;
    border-top: 1px solid var(--border-color);
    display: flex;
    gap: 8px;
  }

  .btn-primary,
  .btn-warning,
  .btn-danger {
    flex: 1;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-primary {
    background: var(--accent);
    color: #fff;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .btn-warning {
    background: #e6a23c;
    color: #fff;
  }

  .btn-warning:hover {
    background: #d4922d;
  }

  .btn-danger {
    background: #e05c6c;
    color: #fff;
  }

  .btn-danger:hover {
    background: #c94d5c;
  }
</style>
