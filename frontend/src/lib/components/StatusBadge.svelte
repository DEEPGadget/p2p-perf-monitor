<script lang="ts">
  import type { SessionStateValue } from '$lib/types/api';

  let { state }: { state: SessionStateValue } = $props();

  const labels: Record<SessionStateValue, string> = {
    idle: 'IDLE',
    connecting: 'CONNECTING',
    running: 'RUNNING',
    error: 'ERROR',
  };
</script>

<div class="badge {state}">
  <span class="dot"></span>
  <span class="text">{labels[state]}</span>
</div>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.1em;
    color: var(--color-muted);
    transition: all 0.3s ease;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-muted);
    transition: all 0.3s ease;
  }
  .badge.running {
    border-color: var(--color-accent);
    color: var(--color-accent);
    animation: pulse-glow 1.4s ease-in-out infinite;
  }
  .badge.running .dot {
    background: var(--color-accent);
    box-shadow: 0 0 12px var(--color-accent);
  }
  .badge.error {
    border-color: var(--color-danger);
    color: var(--color-danger);
  }
  .badge.error .dot { background: var(--color-danger); }
  .badge.connecting {
    border-color: var(--color-warning);
    color: var(--color-warning);
  }
  .badge.connecting .dot { background: var(--color-warning); }
</style>
