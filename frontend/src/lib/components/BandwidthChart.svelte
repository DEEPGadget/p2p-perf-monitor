<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import { measurementStore } from '$lib/stores/measurement.svelte';
  import { sessionStore } from '$lib/stores/session.svelte';

  let { bidir = false }: { bidir?: boolean } = $props();

  let container: HTMLDivElement | undefined = $state();
  let chart: import('echarts').ECharts | null = null;

  const yMax = $derived(bidir ? 400 : 200);
  const yInterval = $derived(bidir ? 100 : 50);

  function baseOption() {
    return {
      animation: false,
      grid: { left: 50, right: 16, top: 16, bottom: 32 },
      xAxis: {
        type: 'category',
        data: [] as string[],
        axisLabel: { color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
        axisLine: { lineStyle: { color: '#262626' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: yMax,
        interval: yInterval,
        axisLabel: { color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, formatter: '{value}' },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#1c1c1c' } },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#141414',
        borderColor: '#262626',
        textStyle: { color: '#fff', fontFamily: 'JetBrains Mono, monospace' },
      },
      series: [
        {
          type: 'line',
          data: [] as number[],
          smooth: false,
          symbol: 'none',
          lineStyle: { color: '#00d9ff', width: 2.5, shadowColor: '#00d9ff', shadowBlur: 8 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(0, 217, 255, 0.35)' },
                { offset: 1, color: 'rgba(0, 217, 255, 0)' },
              ],
            },
          },
        },
      ],
    };
  }

  onMount(async () => {
    const echarts = await import('echarts');
    if (container) {
      chart = echarts.init(container, null, { renderer: 'canvas' });
      chart.setOption(baseOption());
    }
    const ro = new ResizeObserver(() => chart?.resize());
    if (container) ro.observe(container);
  });

  onDestroy(() => {
    chart?.dispose();
    chart = null;
  });

  // 데이터 push 시 chart 업데이트
  $effect(() => {
    if (!chart) return;
    chart.setOption(
      {
        xAxis: { data: measurementStore.labels },
        series: [{ data: measurementStore.values }],
      },
      { lazyUpdate: true },
    );
  });

  // bidir 변경 시 Y축 max
  $effect(() => {
    chart?.setOption({ yAxis: { max: yMax, interval: yInterval } });
  });
</script>

<section class="chart-wrap">
  <div class="chart-header">
    <div class="chart-title">BANDWIDTH (Gb/s) — LAST 60s</div>
    <div class="chart-live" style:opacity={sessionStore.state === 'running' ? 1 : 0}>
      <span class="dot"></span>
      <span>LIVE</span>
    </div>
  </div>
  <div class="chart" bind:this={container}></div>
</section>

<style>
  .chart-wrap {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    padding: 20px 24px;
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
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-accent);
    box-shadow: 0 0 8px var(--color-accent);
    animation: blink 1.4s ease-in-out infinite;
  }
  .chart {
    flex: 1;
    min-height: 0;
  }
</style>
