<script lang="ts">
  import gsap from 'gsap';
  import { onDestroy } from 'svelte';

  import { nicTelemetryStore, severity } from '$lib/stores/nic_telemetry.svelte';
  import { sessionStore } from '$lib/stores/session.svelte';
  import { formatCelsius } from '$lib/utils/format';

  let { bidir = $bindable(false) } = $props<{ bidir?: boolean }>();

  // SVG element refs
  let packetsGroup: SVGGElement | undefined = $state();
  let linkUp: SVGLineElement | undefined = $state();
  let linkDown: SVGLineElement | undefined = $state();
  let linkLabel: SVGTextElement | undefined = $state();

  // Reactive: 측정 시작/정지에 따라 packet flow on/off
  let isRunning = $derived(sessionStore.state === 'running');
  $effect(() => {
    if (isRunning) {
      startFlow(bidir);
    } else {
      stopFlow();
    }
  });

  // Bidir 토글 시 라인 위치 변경
  $effect(() => {
    applyBidirLayout(bidir);
  });

  // 색상 코딩 (NIC overlay)
  const sevA = $derived(severity(nicTelemetryStore.icA, 'ic'));
  const sevB = $derived(severity(nicTelemetryStore.icB, 'ic'));
  const sevModA = $derived(severity(nicTelemetryStore.modA, 'module'));
  const sevModB = $derived(severity(nicTelemetryStore.modB, 'module'));

  function applyBidirLayout(on: boolean): void {
    if (!linkUp || !linkDown || !linkLabel) return;
    if (on) {
      linkUp.setAttribute('y1', '160');
      linkUp.setAttribute('y2', '160');
      linkDown.setAttribute('y1', '180');
      linkDown.setAttribute('y2', '180');
      linkDown.style.visibility = '';
      linkLabel.setAttribute('y', '138');
    } else {
      linkUp.setAttribute('y1', '170');
      linkUp.setAttribute('y2', '170');
      linkDown.style.visibility = 'hidden';
      linkLabel.setAttribute('y', '148');
    }
  }

  function createDot(cy: number, fromX: number, toX: number, delay: number): SVGCircleElement {
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('class', 'packet-dot');
    dot.setAttribute('r', '4');
    dot.setAttribute('cy', String(cy));
    dot.setAttribute('cx', String(fromX));
    dot.setAttribute('opacity', '0');
    packetsGroup?.appendChild(dot);
    gsap.to(dot, {
      attr: { cx: toX },
      opacity: 1,
      duration: 1.5,
      delay,
      repeat: -1,
      ease: 'none',
      onRepeat: () => gsap.set(dot, { attr: { cx: fromX } }),
    });
    gsap.to(dot, {
      opacity: 0,
      duration: 0.3,
      delay: delay + 1.2,
      repeat: -1,
    });
    return dot;
  }

  function startFlow(bidirOn: boolean): void {
    if (!packetsGroup || !linkUp || !linkDown) return;
    if (bidirOn) {
      for (let i = 0; i < 5; i++) {
        createDot(160, 800, 1020, i * 0.25);
        createDot(180, 1020, 800, i * 0.25 + 0.125);
      }
      gsap.to([linkUp, linkDown], { attr: { 'stroke-width': 3.5 }, css: { stroke: '#00d9ff' }, duration: 0.4 });
    } else {
      for (let i = 0; i < 5; i++) {
        createDot(170, 800, 1020, i * 0.25);
      }
      gsap.to(linkUp, { attr: { 'stroke-width': 3.5 }, css: { stroke: '#00d9ff' }, duration: 0.4 });
    }
  }

  function stopFlow(): void {
    if (!packetsGroup || !linkUp || !linkDown) return;
    gsap.killTweensOf('.packet-dot');
    while (packetsGroup.firstChild) packetsGroup.removeChild(packetsGroup.firstChild);
    gsap.to([linkUp, linkDown], { attr: { 'stroke-width': 2.5 }, css: { stroke: '#262626' }, duration: 0.4 });
  }

  onDestroy(() => stopFlow());
</script>

<section class="hardware">
  <svg class="hardware-svg" viewBox="0 0 1820 280" preserveAspectRatio="xMidYMid meet">
    <!-- Server A: dg5W -->
    <rect class="server-box" x="60" y="20" width="540" height="240" />
    <text class="server-label" x="330" y="55" text-anchor="middle">dg5W-H200NVL-4</text>
    <text class="liquid-tag" x="330" y="80" text-anchor="middle"
      ><tspan class="icon">◇</tspan>&nbsp;&nbsp;LIQUID-COOLED</text>
    <rect class="cpu-ram-box" x="90" y="100" width="120" height="42" />
    <text class="cpu-ram-text" x="150" y="120" text-anchor="middle">EPYC 9124</text>
    <text class="cpu-ram-sub" x="150" y="135" text-anchor="middle">16C / 1S</text>
    <rect class="cpu-ram-box" x="225" y="100" width="120" height="42" />
    <text class="cpu-ram-text" x="285" y="120" text-anchor="middle">512 GB</text>
    <text class="cpu-ram-sub" x="285" y="135" text-anchor="middle">DDR5</text>
    <rect class="cpu-ram-box" x="360" y="100" width="210" height="42" />
    <text class="cpu-ram-text" x="465" y="126" text-anchor="middle">PCIe5 x16</text>
    <rect class="nic-box" x="90" y="160" width="480" height="44" />
    <text class="nic-label" x="330" y="188" text-anchor="middle">ConnectX-6 · mlx5_0</text>
    <line class="nic-temp-divider" x1="90" y1="220" x2="570" y2="220" />
    <text class="nic-temp-tag" x="100" y="244" text-anchor="start">IC TEMP</text>
    <text class="nic-temp-overlay {sevA.cssClass}" x="560" y="244" text-anchor="end">{formatCelsius(nicTelemetryStore.icA)}°C</text>

    <!-- Server B: dg5R -->
    <rect class="server-box" x="1220" y="20" width="540" height="240" />
    <text class="server-label" x="1490" y="55" text-anchor="middle">dg5R-PRO6000SE-8</text>
    <text class="liquid-tag" x="1490" y="80" text-anchor="middle"
      ><tspan class="icon">◇</tspan>&nbsp;&nbsp;LIQUID-COOLED</text>
    <rect class="cpu-ram-box" x="1250" y="100" width="120" height="42" />
    <text class="cpu-ram-text" x="1310" y="120" text-anchor="middle">Xeon 6747P</text>
    <text class="cpu-ram-sub" x="1310" y="135" text-anchor="middle">96C / 2S</text>
    <rect class="cpu-ram-box" x="1385" y="100" width="120" height="42" />
    <text class="cpu-ram-text" x="1445" y="120" text-anchor="middle">512 GB</text>
    <text class="cpu-ram-sub" x="1445" y="135" text-anchor="middle">DDR5</text>
    <rect class="cpu-ram-box" x="1520" y="100" width="210" height="42" />
    <text class="cpu-ram-text" x="1625" y="126" text-anchor="middle">PCIe5 x16</text>
    <rect class="nic-box" x="1250" y="160" width="480" height="44" />
    <text class="nic-label" x="1490" y="188" text-anchor="middle">ConnectX-6 · rocep100s0f0</text>
    <line class="nic-temp-divider" x1="1250" y1="220" x2="1730" y2="220" />
    <text class="nic-temp-tag" x="1260" y="244" text-anchor="start">IC TEMP</text>
    <text class="nic-temp-overlay {sevB.cssClass}" x="1720" y="244" text-anchor="end">{formatCelsius(nicTelemetryStore.icB)}°C</text>

    <!-- Transceivers -->
    <rect class="transceiver-box" x="640" y="120" width="160" height="100" />
    <text class="transceiver-label" x="720" y="145" text-anchor="middle">QSFP56</text>
    <text class="transceiver-sub" x="720" y="163" text-anchor="middle">OPTICAL · LIQUID-COOLED</text>
    <line class="nic-temp-divider" x1="650" y1="178" x2="790" y2="178" />
    <text class="nic-temp-tag" x="660" y="196" text-anchor="start">MODULE</text>
    <text class="module-temp-overlay {sevModA.cssClass}" x="785" y="196" text-anchor="end">{formatCelsius(nicTelemetryStore.modA)}°C</text>

    <rect class="transceiver-box" x="1020" y="120" width="160" height="100" />
    <text class="transceiver-label" x="1100" y="145" text-anchor="middle">QSFP56</text>
    <text class="transceiver-sub" x="1100" y="163" text-anchor="middle">OPTICAL · LIQUID-COOLED</text>
    <line class="nic-temp-divider" x1="1030" y1="178" x2="1170" y2="178" />
    <text class="nic-temp-tag" x="1040" y="196" text-anchor="start">MODULE</text>
    <text class="module-temp-overlay {sevModB.cssClass}" x="1165" y="196" text-anchor="end">{formatCelsius(nicTelemetryStore.modB)}°C</text>

    <!-- Stub lines NIC ↔ Transceiver -->
    <line class="link-line" x1="570" y1="182" x2="640" y2="170" />
    <line class="link-line" x1="1180" y1="170" x2="1250" y2="182" />

    <!-- Main links (UNI=1, BIDIR=2) -->
    <line bind:this={linkUp} class="link-line" x1="800" y1="170" x2="1020" y2="170" />
    <line bind:this={linkDown} class="link-line" x1="800" y1="180" x2="1020" y2="180" style="visibility: hidden" />
    <text bind:this={linkLabel} class="link-label" x="910" y="148" text-anchor="middle">200G ROCE V2 · MTU 9000</text>

    <g bind:this={packetsGroup}></g>
  </svg>
</section>

<style>
  .hardware {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    position: relative;
    overflow: hidden;
    padding: 16px 24px;
  }
  .hardware-svg { width: 100%; height: 100%; overflow: visible; }
  .server-box { fill: var(--color-surface-2); stroke: var(--color-border); stroke-width: 1.5; rx: 10; }
  .server-label { fill: var(--color-text); font-family: var(--font-mono); font-size: 22px; font-weight: 800; letter-spacing: 0.06em; }
  .liquid-tag { fill: var(--color-muted); font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; }
  .liquid-tag .icon { fill: var(--color-accent); }
  .nic-box { fill: var(--color-bg); stroke: var(--color-accent); stroke-width: 1.2; rx: 6; opacity: 0.7; }
  .nic-label { fill: var(--color-accent); font-family: var(--font-mono); font-size: 16px; font-weight: 700; letter-spacing: 0.08em; }
  .link-line { stroke: var(--color-border); stroke-width: 2.5; stroke-linecap: round; }
  .link-label { fill: var(--color-muted); font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 600; }
  :global(.packet-dot) { fill: var(--color-accent); filter: drop-shadow(0 0 5px var(--color-accent)); }
  .cpu-ram-box { fill: var(--color-bg); stroke: var(--color-border); stroke-width: 1; rx: 4; }
  .cpu-ram-text { fill: var(--color-text-2); font-family: var(--font-mono); font-size: 11px; font-weight: 600; letter-spacing: 0.05em; }
  .cpu-ram-sub  { fill: var(--color-muted);  font-family: var(--font-mono); font-size: 9px;  font-weight: 500; letter-spacing: 0.05em; }
  .transceiver-box { fill: var(--color-bg); stroke: var(--color-accent); stroke-width: 1; rx: 5; opacity: 0.8; }
  .transceiver-label { fill: var(--color-text-2); font-family: var(--font-mono); font-size: 12px; font-weight: 700; letter-spacing: 0.1em; }
  .transceiver-sub { fill: var(--color-muted); font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.15em; text-transform: uppercase; }
  .nic-temp-overlay { fill: var(--color-accent); font-family: var(--font-mono); font-size: 18px; font-weight: 700; letter-spacing: 0.05em; }
  .nic-temp-overlay.warn { fill: var(--color-warning); }
  .nic-temp-overlay.danger { fill: var(--color-danger); }
  .nic-temp-tag { fill: var(--color-muted); font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 600; }
  .nic-temp-divider { stroke: var(--color-border); stroke-width: 1; opacity: 0.6; }
  .module-temp-overlay { fill: var(--color-accent); font-family: var(--font-mono); font-size: 14px; font-weight: 700; letter-spacing: 0.05em; }
  .module-temp-overlay.warn { fill: var(--color-warning); }
  .module-temp-overlay.danger { fill: var(--color-danger); }
</style>
