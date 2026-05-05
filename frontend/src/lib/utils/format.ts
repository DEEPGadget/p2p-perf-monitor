/** 숫자 포매팅 헬퍼 — KPI 카드 / 다이어그램 overlay 공통. */

export function formatGbps(v: number, decimals = 1): string {
  return v.toFixed(decimals);
}

export function formatUs(v: number, decimals = 2): string {
  return v.toFixed(decimals);
}

export function formatCelsius(v: number | null | undefined, decimals = 1): string {
  if (v == null) return '—';
  return v.toFixed(decimals);
}

export function formatTime(d: Date = new Date()): string {
  const h = String(d.getHours()).padStart(2, '0');
  const m = String(d.getMinutes()).padStart(2, '0');
  const s = String(d.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}
