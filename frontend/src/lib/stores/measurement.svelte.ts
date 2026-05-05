/** 측정 이벤트 store — BW/Lat 시계열 버퍼 + KPI 파생값.
 *
 * tool category 에 따라 차트는 BW (Gb/s) 또는 Latency (µs) 시계열을 표시.
 * `mode`: 'bw' | 'lat' — 마지막 push 의 sub_tool 로 결정.
 */

import type { MeasurementEvent, ToolKind } from '$lib/types/api';

const MAX_POINTS = 600; // 60초 @ 10Hz 또는 120초 @ 5Hz

export type ChartMode = 'bw' | 'lat';

class MeasurementStore {
  // BW 시계열 (Gb/s)
  labels: string[] = $state([]);
  values: number[] = $state([]);

  // Latency 시계열 (µs)
  latLabels: string[] = $state([]);
  latValues: number[] = $state([]);

  // 마지막 push 의 sub_tool 기반 mode (chart 분기용)
  mode: ChartMode = $state('bw');

  // KPI 파생값
  current: number = $state(0);
  average: number = $state(0);
  peak: number = $state(0);
  latency: number | null = $state(null);

  startTimeMs = 0;

  reset(): void {
    this.labels = [];
    this.values = [];
    this.latLabels = [];
    this.latValues = [];
    this.mode = 'bw';
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

    const isLat: boolean = (evt.sub_tool as ToolKind | null) === 'ib_read_lat';
    this.mode = isLat ? 'lat' : 'bw';

    if (isLat && evt.lat_us !== null) {
      this.latLabels = [...this.latLabels, label].slice(-MAX_POINTS);
      this.latValues = [...this.latValues, evt.lat_us].slice(-MAX_POINTS);
      this.latency = evt.lat_us;
    } else {
      const bw = evt.bw_avg_gbps;
      this.labels = [...this.labels, label].slice(-MAX_POINTS);
      this.values = [...this.values, bw].slice(-MAX_POINTS);
      this.current = bw;
      if (bw > this.peak) this.peak = bw;
      const sum = this.values.reduce((a, b) => a + b, 0);
      this.average = this.values.length > 0 ? sum / this.values.length : 0;
      if (evt.lat_us !== null) this.latency = evt.lat_us;
    }
  }
}

export const measurementStore = new MeasurementStore();
