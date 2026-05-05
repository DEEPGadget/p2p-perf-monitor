/** SSE 구독 — /api/stream 의 4 이벤트(measurement/nic_temp/status/error) 분기.
 *
 * Spec → rules/api.md §SSE 포맷, rules/frontend.md.
 * EventSource 자동 재연결 사용. 사용자가 close 호출 시까지 유지.
 */

import type {
  ErrorEvent as ApiErrorEvent,
  MeasurementEvent,
  NicTelemetry,
  SessionStatus,
} from '$lib/types/api';

export interface SseHandlers {
  onMeasurement?: (e: MeasurementEvent) => void;
  onNicTemp?: (e: NicTelemetry) => void;
  onStatus?: (e: SessionStatus) => void;
  onError?: (e: ApiErrorEvent) => void;
}

export function subscribeSse(handlers: SseHandlers): () => void {
  const es = new EventSource('/api/stream');

  if (handlers.onMeasurement) {
    es.addEventListener('measurement', (e) => {
      try {
        handlers.onMeasurement!(JSON.parse((e as MessageEvent).data));
      } catch {
        // ignore malformed
      }
    });
  }
  if (handlers.onNicTemp) {
    es.addEventListener('nic_temp', (e) => {
      try {
        handlers.onNicTemp!(JSON.parse((e as MessageEvent).data));
      } catch {
        // ignore
      }
    });
  }
  if (handlers.onStatus) {
    es.addEventListener('status', (e) => {
      try {
        handlers.onStatus!(JSON.parse((e as MessageEvent).data));
      } catch {
        // ignore
      }
    });
  }
  if (handlers.onError) {
    es.addEventListener('error', (e) => {
      // EventSource error event 는 종종 데이터 없는 connection error
      const msg = e as MessageEvent;
      if (typeof msg.data === 'string') {
        try {
          handlers.onError!(JSON.parse(msg.data));
        } catch {
          // ignore
        }
      }
    });
  }

  return () => es.close();
}
