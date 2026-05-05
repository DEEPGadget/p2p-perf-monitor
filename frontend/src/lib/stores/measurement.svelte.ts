/** BW 측정 이벤트 store — 시계열 버퍼 + KPI 파생값. */

import type { MeasurementEvent } from '$lib/types/api';

const MAX_POINTS = 600; // 60초 @ 10Hz 또는 120초 @ 5Hz

class MeasurementStore {
  // 시계열 (chart 용)
  labels: string[] = $state([]);
  values: number[] = $state([]);

  // KPI 파생값
  current: number = $state(0);
  average: number = $state(0);
  peak: number = $state(0);
  latency: number | null = $state(null);

  startTimeMs = 0;

  reset(): void {
    this.labels = [];
    this.values = [];
    this.current = 0;
    this.average = 0;
    this.peak = 0;
    this.latency = null;
    this.startTimeMs = Date.now();
  }

  push(evt: MeasurementEvent): void {
    if (this.startTimeMs === 0) this.startTimeMs = Date.now();
    const elapsed = (Date.now() - this.startTimeMs) / 1000;
    const label = `${elapsed.toFixed(0)}s`;
    const bw = evt.bw_avg_gbps;

    this.labels = [...this.labels, label].slice(-MAX_POINTS);
    this.values = [...this.values, bw].slice(-MAX_POINTS);

    this.current = bw;
    if (bw > this.peak) this.peak = bw;
    const sum = this.values.reduce((a, b) => a + b, 0);
    this.average = this.values.length > 0 ? sum / this.values.length : 0;
    if (evt.lat_us !== null) {
      this.latency = evt.lat_us;
    }
  }
}

export const measurementStore = new MeasurementStore();
