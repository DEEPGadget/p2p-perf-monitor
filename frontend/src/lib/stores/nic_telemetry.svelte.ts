/** NIC IC + Module 온도 store — 4채널 시계열 + 현재값. */

import type { NicTelemetry } from '$lib/types/api';

const MAX_POINTS = 600;

export interface SeverityLevel {
  level: 'normal' | 'warn' | 'danger' | 'unknown';
  cssClass: string;
}

/** 임계값 → rules/measurement.md §임계값. */
export function severity(value: number | null, kind: 'ic' | 'module'): SeverityLevel {
  if (value == null) return { level: 'unknown', cssClass: '' };
  const warn = kind === 'module' ? 65 : 75;
  const danger = kind === 'module' ? 75 : 85;
  if (value >= danger) return { level: 'danger', cssClass: 'danger' };
  if (value >= warn) return { level: 'warn', cssClass: 'warn' };
  return { level: 'normal', cssClass: '' };
}

class NicTelemetryStore {
  // 현재값 (타일·다이어그램 overlay)
  icA: number | null = $state(null);
  icB: number | null = $state(null);
  modA: number | null = $state(null);
  modB: number | null = $state(null);

  // 시계열 (4 라인 chart)
  labels: string[] = $state([]);
  icAValues: (number | null)[] = $state([]);
  icBValues: (number | null)[] = $state([]);
  modAValues: (number | null)[] = $state([]);
  modBValues: (number | null)[] = $state([]);

  startTimeMs = 0;

  resetSeries(): void {
    this.labels = [];
    this.icAValues = [];
    this.icBValues = [];
    this.modAValues = [];
    this.modBValues = [];
    this.startTimeMs = Date.now();
  }

  /** 현재값만 갱신 (IDLE 상태 — 타일·overlay만). */
  updateCurrent(t: NicTelemetry): void {
    this.icA = t.server_a_ic_c;
    this.icB = t.server_b_ic_c;
    this.modA = t.server_a_module_c;
    this.modB = t.server_b_module_c;
  }

  /** 현재값 갱신 + 시계열 push (RUNNING 시). */
  push(t: NicTelemetry): void {
    this.updateCurrent(t);
    if (this.startTimeMs === 0) this.startTimeMs = Date.now();
    const elapsed = (Date.now() - this.startTimeMs) / 1000;
    const label = `${elapsed.toFixed(0)}s`;
    this.labels = [...this.labels, label].slice(-MAX_POINTS);
    this.icAValues = [...this.icAValues, t.server_a_ic_c].slice(-MAX_POINTS);
    this.icBValues = [...this.icBValues, t.server_b_ic_c].slice(-MAX_POINTS);
    this.modAValues = [...this.modAValues, t.server_a_module_c].slice(-MAX_POINTS);
    this.modBValues = [...this.modBValues, t.server_b_module_c].slice(-MAX_POINTS);
  }
}

export const nicTelemetryStore = new NicTelemetryStore();
