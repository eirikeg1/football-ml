<script lang="ts">
  import TrainingConfigPanel from "./training/TrainingConfigPanel.svelte";
  import TrainingDashboard from "./training/TrainingDashboard.svelte";
</script>

<div class="training-view">
  <TrainingConfigPanel />
  <TrainingDashboard />
</div>

<style>
  .training-view {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
</style>
