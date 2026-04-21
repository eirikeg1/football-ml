<script lang="ts">
  import { Chart, registerables } from "chart.js";

  Chart.register(...registerables);

  interface Props {
    label: string;
    values: number[];
    color?: string;
  }

  let { label, values, color = "#4ade80" }: Props = $props();

  let canvasEl: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (!canvasEl) return;
    chart = new Chart(canvasEl, {
      type: "line",
      data: {
        labels: values.map((_, i) => i + 1),
        datasets: [
          {
            label,
            data: [...values],
            borderColor: color,
            backgroundColor: `${color}1a`,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            fill: true,
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
            title: { display: true, text: label, color: "#5a6577" },
            ticks: { color: "#5a6577" },
            grid: { color: "rgba(42, 58, 92, 0.5)" },
          },
        },
      },
    });
  }

  $effect(() => {
    if (!chart && canvasEl && values.length > 0) {
      createChart();
    } else if (chart) {
      chart.data.labels = values.map((_, i) => i + 1);
      chart.data.datasets[0].data = [...values];
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
    height: 180px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
  }
</style>
