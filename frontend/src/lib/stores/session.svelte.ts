/** Svelte 5 runes 기반 세션 상태 store. */

import type { SessionStatus, SessionStateValue, ToolKind } from '$lib/types/api';

class SessionStore {
  state: SessionStateValue = $state('idle');
  tool: ToolKind | null = $state(null);
  startedAt: string | null = $state(null);
  errorMsg: string | null = $state(null);

  update(s: SessionStatus): void {
    this.state = s.state;
    this.tool = s.tool;
    this.startedAt = s.started_at;
    this.errorMsg = s.error ? JSON.stringify(s.error) : null;
  }

  reset(): void {
    this.state = 'idle';
    this.tool = null;
    this.startedAt = null;
    this.errorMsg = null;
  }
}

export const sessionStore = new SessionStore();
