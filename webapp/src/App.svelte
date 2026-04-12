<script lang="ts">
  import Toolbar from "./components/Toolbar.svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import Canvas from "./components/Canvas.svelte";
  import DetailPanel from "./components/DetailPanel.svelte";
</script>

<div class="app">
  <Toolbar />
  <div class="main">
    <Sidebar />
    <Canvas />
    <DetailPanel />
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
