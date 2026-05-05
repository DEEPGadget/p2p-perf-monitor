<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import BandwidthChart from '$lib/components/BandwidthChart.svelte';
  import ControlPanel from '$lib/components/ControlPanel.svelte';
  import HardwareDiagram from '$lib/components/HardwareDiagram.svelte';
  import Header from '$lib/components/Header.svelte';
  import KpiCards from '$lib/components/KpiCards.svelte';
  import NicTempPanel from '$lib/components/NicTempPanel.svelte';
  import { measurementStore } from '$lib/stores/measurement.svelte';
  import { nicTelemetryStore } from '$lib/stores/nic_telemetry.svelte';
  import { sessionStore } from '$lib/stores/session.svelte';
  import { apiStatus } from '$lib/utils/api';
  import { subscribeSse } from "$lib/utils/sse";

  let bidir = $state(false);
  let unsubscribe: (() => void) | undefined;

  // 측정 시작 시 store reset (status running 진입 감지)
  let prevState = $state(sessionStore.state);
  $effect(() => {
    const cur = sessionStore.state;
    if (cur === 'running' && prevState !== 'running') {
      measurementStore.reset();
      nicTelemetryStore.resetSeries();
    }
    prevState = cur;
  });

  onMount(async () => {
    // 초기 status 동기화
    try {
      const s = await apiStatus();
      sessionStore.update(s);
    } catch {
      // ignore
    }
    // SSE 구독
    unsubscribe = subscribeSse({
      onMeasurement: (e) => measurementStore.push(e),
      onNicTemp: (e) => {
        if (sessionStore.state === 'running') {
          nicTelemetryStore.push(e);
        } else {
          nicTelemetryStore.updateCurrent(e);
        }
      },
      onStatus: (e) => sessionStore.update(e),
      onError: (e) => console.error('sse error event', e),
    });
  });

  onDestroy(() => {
    if (unsubscribe) unsubscribe();
  });
</script>

<div class="app">
  <Header />
  <main>
    <HardwareDiagram bind:bidir />
    <KpiCards />
    <section class="chart-row">
      <BandwidthChart {bidir} />
      <NicTempPanel />
    </section>
    <ControlPanel sessionState={sessionStore.state} bind:bidir />
  </main>
  <footer>
    <div class="meta">
      <span>NIC mlx5_0 ↔ mlx5_0</span>
      <span>·</span>
      <span>RoCE v2</span>
      <span>·</span>
      <span>MTU 9000</span>
    </div>
    <div class="meta">
      <span>v0.1</span>
    </div>
  </footer>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  main {
    flex: 1;
    display: grid;
    grid-template-rows: 280px 200px 1fr 96px;
    gap: 20px;
    padding: 20px 40px;
    overflow: hidden;
  }
  .chart-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 24px;
    min-height: 0;
  }
  footer {
    height: 32px;
    flex-shrink: 0;
    border-top: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    font-size: 11px;
    color: var(--color-muted);
    font-family: var(--font-mono);
    letter-spacing: 0.05em;
  }
  .meta {
    display: flex;
    gap: 16px;
    align-items: center;
  }
  .meta.brand { gap: 14px; }
  .brand-logo {
    height: 22px;
    width: auto;
    display: block;
    /* 흰 배경 PNG 라도 dark 테마에 자연스럽게 — 명도 유지하며 파란색 보존 */
    filter: brightness(1.05);
  }
  .meta .version {
    font-size: 11px;
    color: var(--color-muted);
    letter-spacing: 0.05em;
  }
</style>
