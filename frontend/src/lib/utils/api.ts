/** REST API 클라이언트 — POST /api/start, /api/stop, GET /api/status. */

import type { SessionStatus, StartRequest } from '$lib/types/api';

export async function apiStart(req: StartRequest): Promise<SessionStatus> {
  const r = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    throw new Error(`start failed: ${r.status} ${await r.text()}`);
  }
  return await r.json();
}

export async function apiStop(): Promise<SessionStatus> {
  const r = await fetch('/api/stop', { method: 'POST' });
  if (!r.ok) {
    throw new Error(`stop failed: ${r.status}`);
  }
  return await r.json();
}

export async function apiStatus(): Promise<SessionStatus> {
  const r = await fetch('/api/status');
  if (!r.ok) {
    throw new Error(`status failed: ${r.status}`);
  }
  return await r.json();
}
