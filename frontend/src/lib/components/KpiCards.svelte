<script lang="ts">
  import { measurementStore } from '$lib/stores/measurement.svelte';
  import { formatGbps, formatUs } from '$lib/utils/format';

  // 'NOW' 카드 hot effect — UNI 195+ 또는 BIDIR 380+ 감지 시
  let hot = $state(false);
  let hotTimer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    const cur = measurementStore.current;
    if (cur >= 195) {
      hot = true;
      if (hotTimer) clearTimeout(hotTimer);
      hotTimer = setTimeout(() => (hot = false), 1500);
    }
  });
</script>

<section class="kpi">
  <div class="card" class:hot>
    <div class="card-bg"></div>
    <div class="card-label">CURRENT BANDWIDTH</div>
    <div class="card-value-row">
      <div class="card-value">{formatGbps(measurementStore.current)}</div>
      <div class="card-unit">Gb/s</div>
    </div>
  </div>
  <div class="card">
    <div class="card-bg"></div>
    <div class="card-label">AVERAGE</div>
    <div class="card-value-row">
      <div class="card-value">{formatGbps(measurementStore.average)}</div>
      <div class="card-unit">Gb/s</div>
    </div>
  </div>
  <div class="card">
    <div class="card-bg"></div>
    <div class="card-label">PEAK</div>
    <div class="card-value-row">
      <div class="card-value">{formatGbps(measurementStore.peak)}</div>
      <div class="card-unit">Gb/s</div>
    </div>
  </div>
  <div class="card">
    <div class="card-bg"></div>
    <div class="card-label">LATENCY</div>
    <div class="card-value-row">
      <div class="card-value">
        {measurementStore.latency != null ? formatUs(measurementStore.latency) : '─'}
      </div>
      <div class="card-unit">µs</div>
    </div>
  </div>
</section>

<style>
  .kpi {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
  }
  .card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    padding: 20px 28px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s ease, box-shadow 0.4s ease;
  }
  .card.hot {
    border-color: var(--color-accent);
    box-shadow: 0 0 32px rgba(0, 217, 255, 0.25);
  }
  .card-label {
    font-size: 13px;
    color: var(--color-text-2);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .card-label::before {
    content: '';
    width: 4px;
    height: 14px;
    background: var(--color-accent);
    border-radius: 2px;
    box-shadow: 0 0 8px var(--color-accent);
  }
  .card-value-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: auto;
  }
  .card-value {
    font-family: var(--font-mono);
    font-size: 72px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
  .card-unit {
    font-family: var(--font-mono);
    font-size: 20px;
    font-weight: 500;
    color: var(--color-muted);
    letter-spacing: 0.05em;
  }
  .card-bg {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 80% 20%, rgba(0, 217, 255, 0.05) 0%, transparent 50%);
    pointer-events: none;
  }
</style>
