<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import { nicTelemetryStore, severity } from '$lib/stores/nic_telemetry.svelte';
  import { sessionStore } from '$lib/stores/session.svelte';
  import { formatCelsius } from '$lib/utils/format';

  let container: HTMLDivElement | undefined = $state();
  let chart: import('echarts').ECharts | null = null;

  const sevIcA = $derived(severity(nicTelemetryStore.icA, 'ic'));
  const sevIcB = $derived(severity(nicTelemetryStore.icB, 'ic'));
  const sevModA = $derived(severity(nicTelemetryStore.modA, 'module'));
  const sevModB = $derived(severity(nicTelemetryStore.modB, 'module'));

  onMount(async () => {
    const echarts = await import('echarts');
    if (container) {
      chart = echarts.init(container, null, { renderer: 'canvas' });
      chart.setOption({
        animation: false,
        grid: { left: 36, right: 12, top: 28, bottom: 24 },
        xAxis: {
          type: 'category',
          data: [],
          boundaryGap: false,
          axisLabel: { color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', fontSize: 9 },
          axisLine: { lineStyle: { color: '#262626' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value', min: 25, max: 90, interval: 15,
          axisLabel: { color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, formatter: '{value}°' },
          axisLine: { show: false }, axisTick: { show: false },
          splitLine: { lineStyle: { color: '#1c1c1c' } },
        },
        legend: {
          data: ['IC · dg5W', 'IC · dg5R', 'MOD · dg5W', 'MOD · dg5R'],
          textStyle: { color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
          top: 0, right: 4, itemWidth: 16, itemHeight: 2, itemGap: 10,
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#141414',
          borderColor: '#262626',
          textStyle: { color: '#fff', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
        },
        series: [
          { name: 'IC · dg5W',  type: 'line', data: [], smooth: true, symbol: 'none', lineStyle: { color: '#00d9ff', width: 2, type: 'solid' } },
          { name: 'IC · dg5R',  type: 'line', data: [], smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 2, type: 'solid' } },
          { name: 'MOD · dg5W', type: 'line', data: [], smooth: true, symbol: 'none', lineStyle: { color: '#00d9ff', width: 1.6, type: 'dashed' } },
          { name: 'MOD · dg5R', type: 'line', data: [], smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.6, type: 'dashed' } },
        ],
      });
    }
    const ro = new ResizeObserver(() => chart?.resize());
    if (container) ro.observe(container);
  });

  onDestroy(() => {
    chart?.dispose();
    chart = null;
  });

  $effect(() => {
    if (!chart) return;
    chart.setOption(
      {
        xAxis: { data: nicTelemetryStore.labels },
        series: [
          { data: nicTelemetryStore.icAValues },
          { data: nicTelemetryStore.icBValues },
          { data: nicTelemetryStore.modAValues },
          { data: nicTelemetryStore.modBValues },
        ],
      },
      { lazyUpdate: true },
    );
  });
</script>

<section class="nic-panel">
  <div class="chart-header">
    <div class="chart-title">
      NIC IC &amp; MODULE TEMPERATURE
      <span class="liquid-badge">◇ LIQUID-COOLED</span>
    </div>
    <div class="chart-live" style:opacity={sessionStore.state === 'running' ? 1 : 0}>
      <span class="dot"></span>
      <span>LIVE</span>
    </div>
  </div>
  <div class="nic-tiles">
    <div class="nic-tile {sevIcA.cssClass}">
      <div class="nic-tile-label">IC · dg5W</div>
      <div class="nic-tile-value-row">
        <span class="nic-tile-value">{formatCelsius(nicTelemetryStore.icA)}</span>
        <span class="nic-tile-unit">°C</span>
      </div>
    </div>
    <div class="nic-tile {sevIcB.cssClass}">
      <div class="nic-tile-label">IC · dg5R</div>
      <div class="nic-tile-value-row">
        <span class="nic-tile-value">{formatCelsius(nicTelemetryStore.icB)}</span>
        <span class="nic-tile-unit">°C</span>
      </div>
    </div>
    <div class="nic-tile module {sevModA.cssClass}">
      <div class="nic-tile-label">MODULE · dg5W</div>
      <div class="nic-tile-value-row">
        <span class="nic-tile-value">{formatCelsius(nicTelemetryStore.modA)}</span>
        <span class="nic-tile-unit">°C</span>
      </div>
    </div>
    <div class="nic-tile module {sevModB.cssClass}">
      <div class="nic-tile-label">MODULE · dg5R</div>
      <div class="nic-tile-value-row">
        <span class="nic-tile-value">{formatCelsius(nicTelemetryStore.modB)}</span>
        <span class="nic-tile-unit">°C</span>
      </div>
    </div>
  </div>
  <div class="nic-chart" bind:this={container}></div>
</section>

<style>
  .nic-panel {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .chart-title {
    font-size: 13px;
    color: var(--color-muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }
  .liquid-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border: 1px solid var(--color-accent);
    color: var(--color-accent);
    border-radius: 999px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.18em;
  }
  .chart-live {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-accent);
    letter-spacing: 0.1em;
    transition: opacity 0.4s ease;
  }
  .chart-live .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--color-accent);
    box-shadow: 0 0 8px var(--color-accent);
    animation: blink 1.4s ease-in-out infinite;
  }
  .nic-tiles {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-auto-rows: 1fr;
    gap: 10px;
    margin: 10px 0 12px;
  }
  .nic-tile {
    background: var(--color-surface-2);
    border: 1px solid var(--color-border);
    border-left: 3px solid var(--color-accent);
    border-radius: 10px;
    padding: 8px 12px;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
  }
  .nic-tile.module { border-left-style: dashed; }
  .nic-tile.warn {
    border-left-color: var(--color-warning);
    box-shadow: 0 0 14px rgba(245, 158, 11, 0.15);
  }
  .nic-tile.danger {
    border-left-color: var(--color-danger);
    box-shadow: 0 0 14px rgba(239, 68, 68, 0.25);
  }
  .nic-tile-label {
    font-size: 9px;
    color: var(--color-muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 4px;
  }
  .nic-tile-value-row {
    display: flex;
    align-items: baseline;
    gap: 4px;
  }
  .nic-tile-value {
    font-family: var(--font-mono);
    font-size: 28px;
    font-weight: 700;
    color: var(--color-text);
    line-height: 1;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
  }
  .nic-tile-unit {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-muted);
    font-weight: 500;
  }
  .nic-chart { flex: 1; min-height: 0; }
</style>
