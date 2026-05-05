<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import { sessionStore } from '$lib/stores/session.svelte';
  import { formatTime } from '$lib/utils/format';

  import StatusBadge from './StatusBadge.svelte';

  let now = $state(formatTime());
  let timer: ReturnType<typeof setInterval> | undefined;

  onMount(() => {
    timer = setInterval(() => {
      now = formatTime();
    }, 1000);
  });
  onDestroy(() => {
    if (timer) clearInterval(timer);
  });
</script>

<header>
  <div class="brand">
    <img src="/manycore_logo_white.png" alt="ManyCore" class="brand-logo" />
    <span class="brand-bar" aria-hidden="true"></span>
    <span class="brand-title">P2P PERF MONITOR</span>
  </div>
  <div class="header-right">
    <StatusBadge state={sessionStore.state} />
    <div class="clock">{now}</div>
  </div>
</header>

<style>
  header {
    height: 72px;
    border-bottom: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    align-items: flex-end;
    gap: 16px;
  }
  .brand-logo {
    height: 26px;
    width: auto;
    display: block;
  }
  .brand-bar {
    width: 1px;
    height: 18px;
    background: var(--color-muted);
    flex-shrink: 0;
    margin-bottom: 1px;
  }
  .brand-title {
    color: var(--color-text-2);
    font-weight: 600;
    font-size: 17px;
    letter-spacing: 0.20em;
    line-height: 1;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .clock {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--color-muted);
    letter-spacing: 0.05em;
  }
</style>
