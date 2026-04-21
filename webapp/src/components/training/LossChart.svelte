<script lang="ts">
  import { Chart, registerables } from "chart.js";

  Chart.register(...registerables);

  interface Props {
    trainLoss: number[];
    valLoss: number[];
  }

  let { trainLoss, valLoss }: Props = $props();

  let canvasEl: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (!canvasEl) return;
    chart = new Chart(canvasEl, {
      type: "line",
      data: {
        labels: trainLoss.map((_, i) => i + 1),
        datasets: [
          {
            label: "Train Loss",
            data: [...trainLoss],
            borderColor: "#f87171",
            backgroundColor: "rgba(248, 113, 113, 0.1)",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
          },
          {
            label: "Val Loss",
            data: [...valLoss],
            borderColor: "#60a5fa",
            backgroundColor: "rgba(96, 165, 250, 0.1)",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 200 },
        plugins: {
          legend: {
            labels: { color: "#8892a4", font: { size: 11 } },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Epoch", color: "#5a6577" },
            ticks: { color: "#5a6577" },
            grid: { color: "rgba(42, 58, 92, 0.5)" },
          },
          y: {
            title: { display: true, text: "Loss", color: "#5a6577" },
            ticks: { color: "#5a6577" },
            grid: { color: "rgba(42, 58, 92, 0.5)" },
          },
        },
      },
    });
  }

  $effect(() => {
    if (!chart && canvasEl && trainLoss.length > 0) {
      createChart();
    } else if (chart) {
      chart.data.labels = trainLoss.map((_, i) => i + 1);
      chart.data.datasets[0].data = [...trainLoss];
      chart.data.datasets[1].data = [...valLoss];
      chart.update("none");
    }
  });

  $effect(() => {
    return () => {
      chart?.destroy();
      chart = null;
    };
  });
</script>

<div class="chart-container">
  <canvas bind:this={canvasEl}></canvas>
</div>

<style>
  .chart-container {
    position: relative;
    height: 220px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
  }
</style>
