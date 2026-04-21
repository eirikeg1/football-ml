<script lang="ts">
  import { trainingState, updateFromEpochResult, appendLog, setStatus } from "../../lib/training-state.svelte";
  import { connectWebSocket, disconnectWebSocket } from "../../lib/training-api";
  import type { WSMessage } from "../../lib/training-types";
  import LossChart from "./LossChart.svelte";
  import MetricChart from "./MetricChart.svelte";
  import ProgressBar from "./ProgressBar.svelte";
  import { onMount } from "svelte";

  let logContainer: HTMLDivElement;

  const STATUS_COLORS: Record<string, string> = {
    idle: "#5a6577",
    training: "#4ade80",
    paused: "#e6a23c",
    completed: "#60a5fa",
    error: "#e05c6c",
  };

  let statusColor = $derived(STATUS_COLORS[trainingState.status] ?? "#5a6577");
  let metricNames = $derived(Object.keys(trainingState.metrics));

  const METRIC_COLORS = ["#4ade80", "#a78bfa", "#f472b6", "#facc15", "#34d399"];

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    const rm = m % 60;
    return `${h}h ${rm}m`;
  }

  let elapsedSeconds = $derived(
    trainingState.epochTimes.reduce((a, b) => a + b, 0)
  );

  let avgEpochTime = $derived(
    trainingState.epochTimes.length > 0
      ? elapsedSeconds / trainingState.epochTimes.length
      : 0
  );

  let etaSeconds = $derived(
    avgEpochTime > 0
      ? avgEpochTime * (trainingState.totalEpochs - trainingState.currentEpoch)
      : 0
  );

  function handleMessage(msg: WSMessage) {
    if (msg.type === "epoch") {
      updateFromEpochResult(msg);
    } else if (msg.type === "status") {
      setStatus(msg.status);
      if (msg.message) {
        appendLog("info", msg.message);
      }
    } else if (msg.type === "log") {
      appendLog(msg.level, msg.message);
    }
  }

  onMount(() => {
    connectWebSocket(
      handleMessage,
      () => { trainingState.wsConnected = true; },
      () => { trainingState.wsConnected = false; },
    );

    return () => {
      disconnectWebSocket();
    };
  });

  // Auto-scroll log
  $effect(() => {
    if (logContainer && trainingState.logs.length > 0) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });
</script>

<div class="dashboard">
  <div class="dashboard-scroll">
    <!-- Status bar -->
    <div class="status-bar">
      <div class="status-left">
        <span class="status-dot" style="background: {statusColor}"></span>
        <span class="status-text">{trainingState.status}</span>
        {#if !trainingState.wsConnected}
          <span class="ws-badge">disconnected</span>
        {/if}
      </div>
      <div class="status-right">
        {#if trainingState.currentEpoch > 0}
          <span class="stat">Epoch: <strong>{trainingState.currentEpoch}/{trainingState.totalEpochs}</strong></span>
          <span class="stat">LR: <strong>{trainingState.currentLR.toExponential(2)}</strong></span>
          <span class="stat">Elapsed: <strong>{formatDuration(elapsedSeconds)}</strong></span>
          {#if trainingState.status === "training" && etaSeconds > 0}
            <span class="stat">ETA: <strong>{formatDuration(etaSeconds)}</strong></span>
          {/if}
        {/if}
      </div>
    </div>

    <!-- Progress -->
    {#if trainingState.totalEpochs > 0}
      <div class="section">
        <ProgressBar current={trainingState.currentEpoch} total={trainingState.totalEpochs} />
      </div>
    {/if}

    <!-- Stat cards -->
    {#if trainingState.trainLoss.length > 0}
      <div class="stat-cards">
        <div class="card">
          <div class="card-label">Train Loss</div>
          <div class="card-value">{trainingState.trainLoss.at(-1)?.toFixed(4) ?? "-"}</div>
        </div>
        <div class="card">
          <div class="card-label">Val Loss</div>
          <div class="card-value">{trainingState.valLoss.at(-1)?.toFixed(4) ?? "-"}</div>
        </div>
        <div class="card">
          <div class="card-label">Best Metric</div>
          <div class="card-value best">{trainingState.bestMetric.toFixed(4)}</div>
        </div>
        <div class="card">
          <div class="card-label">Per Epoch</div>
          <div class="card-value">{avgEpochTime > 0 ? formatDuration(avgEpochTime) : "-"}</div>
        </div>
      </div>
    {/if}

    <!-- Resource usage -->
    {#if trainingState.resources}
      <div class="section">
        <div class="section-title">Resources</div>
        <div class="resource-grid">
          <div class="resource-item">
            <div class="resource-label">CPU</div>
            <div class="resource-bar-track">
              <div class="resource-bar-fill" style="width: {trainingState.resources.cpu_percent}%; background: #60a5fa;"></div>
            </div>
            <div class="resource-value">{trainingState.resources.cpu_percent}%</div>
          </div>
          <div class="resource-item">
            <div class="resource-label">RAM</div>
            <div class="resource-bar-track">
              <div class="resource-bar-fill" style="width: {trainingState.resources.ram_percent}%; background: {trainingState.resources.ram_percent > 80 ? '#f87171' : '#4ade80'};"></div>
            </div>
            <div class="resource-value">{trainingState.resources.ram_used_gb}/{trainingState.resources.ram_total_gb} GB</div>
          </div>
          {#if trainingState.resources.gpu_name}
            <div class="resource-item">
              <div class="resource-label" title={trainingState.resources.gpu_name}>GPU</div>
              <div class="resource-bar-track">
                <div class="resource-bar-fill" style="width: {trainingState.resources.gpu_vram_percent}%; background: #a78bfa;"></div>
              </div>
              <div class="resource-value">{trainingState.resources.gpu_vram_used_gb}/{trainingState.resources.gpu_vram_total_gb} GB</div>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Loss chart -->
    {#if trainingState.trainLoss.length > 0}
      <div class="section">
        <div class="section-title">Loss</div>
        <LossChart trainLoss={trainingState.trainLoss} valLoss={trainingState.valLoss} />
      </div>
    {/if}

    <!-- Metric charts -->
    {#each metricNames as metric, i}
      <div class="section">
        <div class="section-title">{metric}</div>
        <MetricChart
          label={metric}
          values={trainingState.metrics[metric]}
          color={METRIC_COLORS[i % METRIC_COLORS.length]}
        />
      </div>
    {/each}

    <!-- Logs -->
    <div class="section">
      <div class="section-title">Log</div>
      <div class="log-container" bind:this={logContainer}>
        {#if trainingState.logs.length === 0}
          <div class="log-empty">No log messages yet. Start training to see output.</div>
        {:else}
          {#each trainingState.logs as entry}
            <div class="log-line" class:warning={entry.level === "warning"} class:error={entry.level === "error"}>
              <span class="log-time">{entry.timestamp}</span>
              <span class="log-msg">{entry.message}</span>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .dashboard {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dashboard-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    margin-bottom: 12px;
  }

  .status-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-text {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    text-transform: capitalize;
  }

  .ws-badge {
    font-size: 9px;
    color: #e05c6c;
    background: rgba(224, 92, 108, 0.1);
    padding: 1px 6px;
    border-radius: 3px;
  }

  .status-right {
    display: flex;
    gap: 16px;
  }

  .stat {
    font-size: 11px;
    color: var(--text-secondary);
  }

  .stat strong {
    color: var(--text-primary);
    font-family: "JetBrains Mono", "Fira Code", monospace;
  }

  .stat-cards {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .card {
    flex: 1;
    padding: 10px 12px;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }

  .card-label {
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }

  .card-value {
    font-size: 18px;
    font-weight: 600;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--text-primary);
  }

  .card-value.best {
    color: var(--accent);
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
  }

  .log-container {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 8px;
    max-height: 200px;
    overflow-y: auto;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 11px;
  }

  .log-empty {
    color: var(--text-muted);
    text-align: center;
    padding: 12px;
    font-family: inherit;
  }

  .log-line {
    display: flex;
    gap: 8px;
    padding: 1px 0;
    color: var(--text-secondary);
  }

  .log-line.warning {
    color: #e6a23c;
  }

  .log-line.error {
    color: #e05c6c;
  }

  .log-time {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .log-msg {
    word-break: break-word;
  }

  .resource-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 12px;
  }

  .resource-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .resource-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    width: 32px;
    flex-shrink: 0;
  }

  .resource-bar-track {
    flex: 1;
    height: 6px;
    background: var(--bg-primary);
    border-radius: 3px;
    overflow: hidden;
  }

  .resource-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
  }

  .resource-value {
    font-size: 10px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--text-muted);
    min-width: 80px;
    text-align: right;
  }
</style>
