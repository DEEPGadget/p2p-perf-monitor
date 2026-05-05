<script lang="ts">
  import type { SessionStateValue, StartRequest, ToolKind } from '$lib/types/api';
  import { apiStart, apiStop } from '$lib/utils/api';

  let {
    sessionState,
    bidir = $bindable(false),
  }: { sessionState: SessionStateValue; bidir?: boolean } = $props();

  const TOOLS: ToolKind[] = ['ib_write_bw', 'ib_read_lat', 'iperf3', 'mock'];
  const SIZES = [
    { label: '64', val: 64 },
    { label: '1K', val: 1024 },
    { label: '8K', val: 8192 },
    { label: '64K', val: 65536 },
    { label: '256K', val: 262144 },
    { label: '1M', val: 1048576 },
  ];
  const DURATIONS = [30, 60, 120, 300];

  let toolIdx = $state(0);
  let sizeIdx = $state(3); // 64K
  let durIdx = $state(1); // 60s

  const tool = $derived(TOOLS[toolIdx]);
  const size = $derived(SIZES[sizeIdx]);
  const dur = $derived(DURATIONS[durIdx]);
  const dirLabel = $derived(bidir ? 'BIDIR' : 'UNI');
  const isRunning = $derived(sessionState === 'running' || sessionState === 'connecting');

  function cycle<T>(arr: T[], idx: number): number {
    return (idx + 1) % arr.length;
  }

  async function onAction(): Promise<void> {
    if (isRunning) {
      try {
        await apiStop();
      } catch (e) {
        console.error(e);
      }
      return;
    }
    const req: StartRequest = {
      tool,
      duration_sec: dur,
      msg_size: size.val,
      bidir,
    };
    try {
      await apiStart(req);
    } catch (e) {
      console.error('start failed', e);
    }
  }
</script>

<section class="control">
  <button class="btn-action" class:stop={isRunning} type="button" onclick={onAction}>
    <span>{isRunning ? '■' : '▶'}</span>
    <span>{isRunning ? 'STOP' : 'START'}</span>
  </button>

  <button class="control-group" type="button" onclick={() => (toolIdx = cycle(TOOLS, toolIdx))} disabled={isRunning}>
    <div>
      <div class="control-label">TOOL</div>
      <div class="control-value">{tool}</div>
    </div>
    <span class="control-arrow">▾</span>
  </button>

  <button class="control-group" type="button" onclick={() => (sizeIdx = cycle(SIZES, sizeIdx))} disabled={isRunning}>
    <div>
      <div class="control-label">MSG SIZE</div>
      <div class="control-value">{size.label}</div>
    </div>
    <span class="control-arrow">▾</span>
  </button>

  <button class="control-group" type="button" onclick={() => (durIdx = cycle(DURATIONS, durIdx))} disabled={isRunning}>
    <div>
      <div class="control-label">DURATION</div>
      <div class="control-value">{dur}s</div>
    </div>
    <span class="control-arrow">▾</span>
  </button>

  <button
    class="control-group"
    type="button"
    onclick={() => (bidir = !bidir)}
    disabled={isRunning}
  >
    <div>
      <div class="control-label">DIRECTION</div>
      <div class="control-value">{dirLabel}</div>
    </div>
    <span class="control-arrow">▾</span>
  </button>

  <div class="control-spacer"></div>

  <img class="brand-logo" src="/dg_logo.png" alt="deep gadget" />
</section>

<style>
  .control {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 24px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 16px;
  }
  .control-group {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--color-surface-2);
    border: 1px solid var(--color-border);
    border-radius: 10px;
    transition: border-color 0.2s ease;
    cursor: pointer;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .control-group:hover:not(:disabled) {
    border-color: var(--color-accent);
  }
  .control-group:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .control-label {
    font-size: 10px;
    color: var(--color-muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 600;
  }
  .control-value {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--color-text);
    font-weight: 500;
  }
  .control-arrow {
    color: var(--color-muted);
    font-size: 10px;
    margin-left: 4px;
  }
  .control-spacer { flex: 1; }
  .btn-action {
    padding: 12px 36px;
    background: var(--color-accent);
    color: var(--color-bg);
    border: none;
    border-radius: 10px;
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .btn-action:hover {
    box-shadow: 0 0 24px rgba(0, 217, 255, 0.5);
    transform: translateY(-1px);
  }
  .btn-action:active {
    transform: translateY(0);
  }
  .btn-action.stop {
    background: var(--color-danger);
  }
  .btn-action.stop:hover {
    box-shadow: 0 0 24px rgba(239, 68, 68, 0.5);
  }
  .brand-logo {
    height: 96px;
    width: auto;
    display: block;
    margin-right: 8px;
  }
</style>
