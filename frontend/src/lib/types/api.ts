// 백엔드 Pydantic 모델과 1:1 매칭. 정본 → app/schemas.py + rules/measurement.md.

export type ToolKind = 'ib_write_bw' | 'ib_read_lat' | 'iperf3' | 'mock';
export type ToolCategory = 'perftest' | 'iperf3' | 'mock';
export type SessionStateValue = 'idle' | 'connecting' | 'running' | 'error';
export type ErrorCode =
  | 'ssh_unreachable'
  | 'ssh_timeout'
  | 'ssh_auth_failed'
  | 'measure_failed'
  | 'temp_polling_failed'
  | 'parse_failed';
export type NicSource = 'sensors' | 'mock';

export interface StartRequest {
  tool?: ToolKind;
  duration_sec?: number;
  msg_size?: number;
  qp_count?: number;
  iperf3_streams?: number;
  bidir?: boolean;
}

export interface SessionStatus {
  state: SessionStateValue;
  tool: ToolKind | null;
  started_at: string | null; // ISO datetime
  error: Record<string, unknown> | null;
}

export interface MeasurementEvent {
  ts: string;
  msg_size: number;
  iterations: number | null;
  bw_peak_gbps: number;
  bw_avg_gbps: number;
  msg_rate_mpps: number | null;
  lat_us: number | null;
  lat_p99_us: number | null;
  tool_category: ToolCategory;
  sub_tool: ToolKind | null;
}

export interface NicTelemetry {
  ts: string;
  server_a_ic_c: number | null;
  server_b_ic_c: number | null;
  server_a_module_c: number | null;
  server_b_module_c: number | null;
  source: NicSource;
}

export interface ErrorEvent {
  code: ErrorCode;
  message: string;
  host: string | null;
  stderr_tail: string | null;
}

export type SseEvent =
  | { name: 'measurement'; payload: MeasurementEvent }
  | { name: 'nic_temp'; payload: NicTelemetry }
  | { name: 'status'; payload: SessionStatus }
  | { name: 'error'; payload: ErrorEvent };
