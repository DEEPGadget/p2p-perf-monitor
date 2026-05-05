<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import { measurementStore } from '$lib/stores/measurement.svelte';
  import { sessionStore } from '$lib/stores/session.svelte';

  let { bidir = false }: { bidir?: boolean } = $props();

  let container: HTMLDivElement | undefined = $state();
  let chart: import('echarts').ECharts | null = null;

  // 데이터 max 기반 동적 yMax — 50 단위 round-up, 데이터 없을 땐 모드별 baseline.
  const dataPeak = $derived(
    measurementStore.values.length > 0 ? Math.max(...measurementStore.values) : 0,
  );
  const yMax = $derived.by(() => {
    const baseline = bidir ? 400 : 200;
    if (dataPeak === 0) return baseline;
    const padded = dataPeak * 1.15; // 15% headroom
    const rounded = Math.ceil(padded / 50) * 50;
    return Math.max(50, rounded);
  });
  const yInterval = $derived(yMax <= 200 ? 50 : 100);

  function baseOption() {
    return {
      animation: false,
      grid: { left: 50, right: 16, top: 16, bottom: 32 },
      xAxis: {
        type: 'category',
        data: [] as string[],
        axisLabel: {
          color: '#a1a1aa',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          interval: 'auto',
          hideOverlap: true,
        },
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
  // NOTE: $effect 는 첫 run 에 read 한 reactive value 만 tracking 한다.
  // chart guard 가 store read 를 가리면 deps 가 영원히 등록 안 되어 재실행 X.
  $effect(() => {
    const labels = measurementStore.labels;
    const values = measurementStore.values;
    if (!chart) return;
    chart.setOption(
      { xAxis: { data: labels }, series: [{ data: values }] },
      { lazyUpdate: true },
    );
  });

  // bidir / dataPeak 변화에 따른 Y축 갱신
  // NOTE: chart?.setOption(...) 의 인자 평가는 chart 가 null 이면 short-circuit 되어
  // yMax/yInterval read 가 누락 → tracking 안 됨. read 우선.
  $effect(() => {
    const max = yMax;
    const interval = yInterval;
    if (!chart) return;
    chart.setOption({ yAxis: { max, interval } });
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
