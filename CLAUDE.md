# p2p-perf-monitor

서버 2대 간 고속 NIC P2P 통신 성능을 실시간으로 측정·시각화하는 Web 기반 데모 도구. 전시회 시연 용도.

## 핵심 요구

- **대상 환경**: 서버 2대 (각 1× 고속 NIC), 직접 연결 또는 단순 스위치 경유
- **측정 지표**: 실시간 대역폭(min/avg/peak), 지연, 추가 지표는 측정 도구에 따라 확장
- **시각화**: 웹 브라우저 실시간 그래프 + 현재값 카드. 관람객 친화적 UI
- **운영 조건**: 전시 부스에서 무인 가동 가능, 빠른 재시작·복구

## 결정 대기 항목

진행 전 결정 필요:

1. **측정 도구·통신 방식**: RoCE/IB RDMA(`perftest` 계열) / TCP(`iperf3`) / GPUDirect(`nccl-tests`) / 자체 구현
2. **백엔드 스택**: FastAPI(Python) / Node.js / Go
3. **프론트 스택**: React / Vue / Svelte / SvelteKit(풀스택)
4. **실시간 푸시**: WebSocket / SSE
5. **수집 토폴로지**:
   - (A) 한 서버에 웹+수집기 → 양쪽에 SSH 또는 agent로 측정 트리거
   - (B) 각 서버에 agent 띄우고 별도 collector(또는 두 서버 중 하나)에서 집계
6. **NIC 모델·드라이버 사전 조건** (RoCE 시 OFED, IB 시 MLNX_OFED 등)

상세 → `handoff/current-state.md`

## Architecture

> 결정 후 작성. 현재 스캐폴딩 단계.

## Directory

> 결정 후 작성.

## Commands

> 결정 후 작성.

## 완료 워크플로우

1. 프로젝트 표준 테스트·린트 통과
2. 브랜치 push → `gh pr create --base main`
3. main 직접 push 금지 (팀 공유 repo)

브랜치 명명: `feature/`, `fix/`, `chore/`

## Git Repo

`DEEPGadget/p2p-perf-monitor` (public)
