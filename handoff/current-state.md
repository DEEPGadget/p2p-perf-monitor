# Handoff — p2p-perf-monitor

> 최종 업데이트: 2026-05-04
> 이 파일의 범위: **다음 작업 + 결정 사항 + 블로커**. 아키텍처·구현 현황 → 프로젝트 `CLAUDE.md` / `docs/`

---

## 추천 시작점

**다음 작업**: Phase 0 마무리 — 구현 문서 교차검증 1라운드 후 피드백 반영, 그 후 Phase 1 (측정 PoC) 시작

**현재 상태**:
- repo: `DEEPGadget/p2p-perf-monitor` (public, main `eb13e36` initial 골격만)
- 문서 1차 작성 완료:
  - `CLAUDE.md` (Architecture/Directory/Commands/환경변수)
  - `.claude/rules/{code-style, api, measurement, frontend, security, testing}.md` 6종
  - `docs/implementation-plan.md` (Phase 0~5)
  - `docs/ui-ux-spec.md` (디자인 시스템 + 와이어프레임 + 모션)
  - `context/nic-environment.md` (ConnectX-7 200G RoCE)
- GUI 목업: `frontend/` 정적 페이지로 디자인 검증 (예정 또는 진행 중)
- 코드: 미작성

---

## 결정 완료 사항

| # | 항목 | 결정 |
|---|------|------|
| 1 | 측정 도구·통신 방식 | 메인 `ib_write_bw` + `ib_read_lat` (RoCE/RDMA), 옵션 `iperf3` (TCP), `mock` (데모) |
| 2 | 백엔드 | FastAPI + asyncssh + structlog |
| 3 | 프론트 스택 | SvelteKit + Vite + Tailwind v4 + ECharts + GSAP + Lucide |
| 4 | 실시간 푸시 | SSE 단방향 (컨트롤은 일반 POST) |
| 5 | 토폴로지 | 단일 controller (한 서버 겸함) + asyncssh로 양쪽 측정 트리거 |
| 6 | NIC | Mellanox ConnectX-7 200G, RoCE v2, MLNX_OFED 사전 설치 |
| 7 | UI 톤 | 흑백 + cyan(#00d9ff) 강조, KPI 5em+, 모션은 GSAP 풀가속 |

상세 → 각 문서 참조.

---

## 결정 대기 항목 (작업 진행하며 채울 것)

| 항목 | 영향 | 결정 시점 |
|------|------|----------|
| RDMA GID index 정확값 | `measurement.md` perftest `-x` 옵션 | Phase 1 시작 시 `show_gids` 출력으로 확정 |
| 케이블 종류 (DAC/AOC) | 운영 문서 | Phase 4 |
| 직결 vs 스위치 경유 | 측정 결과 해석 | Phase 1 |
| 호스트 플랫폼 (dg5W/dg5R) | 운영 문서 | 부스 결정 시 |
| MLNX_OFED 정확 버전 | 의존성 명시 | 설치 시 확정 |
| 회사 로고 SVG | `frontend/static/logo.svg` | Phase 3 시작 시 사용자 제공 |
| 부스 디스플레이 해상도 (1080p/4K) | 반응형 정책 | Phase 4 |

---

## 다음 액션

1. **GUI 목업 작성·검토** (현재 진행 중 또는 직후)
   - `frontend/` 정적 SvelteKit 페이지 또는 단일 HTML 목업
   - mock 데이터로 디자인 톤·레이아웃·모션 검증
2. **교차검증 1라운드**
   - `arch-plan-reviewer`: 아키텍처 설계 적정성
   - `impl-plan-reviewer`: 모듈 분할·인터페이스 일관성
   - `harness-doc-reviewer`: 룰·CLAUDE.md·계획서 일관성
3. **피드백 반영 PR** → 머지
4. **(필요 시) 추가 교차검증 라운드**
5. **Phase 1 시작**: 브랜치 `feature/measurement-poc`, parser+runner+CLI 스크립트, snapshot fixture

---

## 미처리 이슈

없음 (Phase 0 진행 중).

---

## 참고

- 인스펙션 시스템(`projects/inspection-system`)과는 인프라·코드 모두 별개
- 워크스페이스 룰 (`~/workspace/rules/*.md`)이 본 프로젝트 룰 위에 fallback으로 적용됨
- 본 프로젝트 룰이 워크스페이스 룰과 충돌 시 본 프로젝트 룰 우선 (워크스페이스 `CLAUDE.md` 규칙 우선순위)
