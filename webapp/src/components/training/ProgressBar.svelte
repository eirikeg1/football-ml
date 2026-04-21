<script lang="ts">
  interface Props {
    current: number;
    total: number;
  }

  let { current, total }: Props = $props();

  let pct = $derived(total > 0 ? Math.round((current / total) * 100) : 0);
</script>

<div class="progress-bar">
  <div class="progress-track">
    <div class="progress-fill" style="width: {pct}%"></div>
  </div>
  <span class="progress-label">{current}/{total} ({pct}%)</span>
</div>

<style>
  .progress-bar {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .progress-track {
    flex: 1;
    height: 8px;
    background: var(--bg-primary);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-label {
    font-size: 11px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--text-secondary);
    min-width: 90px;
    text-align: right;
  }
</style>
