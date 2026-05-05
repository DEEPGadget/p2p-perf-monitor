# p2p-perf-monitor

ManyCore DeepGadget 서버 2대(`dg5W-H200NVL-4` / `dg5R-PRO6000SE-8`) 간 200G RoCE P2P 통신 성능을 실시간 측정·시각화하는 Web 기반 데모 도구. 전시회 시연 용도.

## 목적

- 두 서버에 각각 Mellanox ConnectX-6 200G NIC 장착, RoCE v2 P2P 링크
- `perftest`(RDMA) + `iperf3`(TCP) 실시간 대역폭·지연 측정
- NIC IC + 광 트랜시버 모듈 온도 4채널 텔레메트리 (액냉)
- 웹 브라우저에서 실시간 시각화 (1080p 부스 디스플레이, 흑백 + cyan 톤)

## 기술 스택

- **백엔드**: FastAPI + asyncssh + structlog (Python)
- **프론트**: SvelteKit + Tailwind v4 + ECharts + GSAP (TypeScript)
- **푸시**: SSE 단방향 (4 이벤트: `measurement` / `nic_temp` / `status` / `error`)
- **운영**: systemd, 단일 controller (양쪽 SSH 트리거), 폐쇄망 부스

## 상태

**Phase 0 완료** (문서 + GUI 목업 + 교차검증). 다음: Phase 1 — 측정 PoC.
상세 → `handoff/current-state.md`. 구현 계획 → `docs/implementation-plan.md`.

## 디렉터리

자세한 구조는 `CLAUDE.md` §Directory 참조. 정본 파일 매핑 표는 `CLAUDE.md` 상단.

## 라이선스

TBD
