<script lang="ts">
  import Toolbar from "./components/Toolbar.svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import Canvas from "./components/Canvas.svelte";
  import DetailPanel from "./components/DetailPanel.svelte";
  import TrainingView from "./components/TrainingView.svelte";

  let activeView = $state<"design" | "training">("design");
</script>

<div class="app">
  <Toolbar {activeView} onViewChange={(v) => (activeView = v)} />
  <div class="main">
    {#if activeView === "design"}
      <Sidebar />
      <Canvas />
      <DetailPanel />
    {:else}
      <TrainingView />
    {/if}
  </div>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
  }

  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
</style>
