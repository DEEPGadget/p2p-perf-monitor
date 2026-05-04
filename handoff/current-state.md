# Handoff — p2p-perf-monitor

> 최종 업데이트: 2026-05-05
> 이 파일의 범위: **다음 작업 + 결정 사항 + 블로커**. 아키텍처·구현 현황 → 프로젝트 `CLAUDE.md` / `docs/`

---

## 추천 시작점

**다음 작업**: **구현 문서 교차검증 1라운드** (3개 reviewer 에이전트), 피드백 반영 후 Phase 1 (측정 PoC) 시작

**현재 상태**:
- repo: `DEEPGadget/p2p-perf-monitor` (public)
- main `eb13e36` initial 골격
- 작업 브랜치: `chore/phase-0-docs-and-mockup` (PR #1, 미머지)
- **Phase 0 산출물 완성**:
  - `CLAUDE.md` (정본 파일 매핑 표 + Architecture/Directory/Commands/환경변수)
  - `.claude/rules/{code-style, api, measurement, frontend, security, testing}.md` 6종
  - `docs/implementation-plan.md` (Phase 0~5 + 모듈 인터페이스)
  - `docs/ui-ux-spec.md` (디자인 시스템 + 와이어프레임 + 모션 timeline)
  - `context/nic-environment.md` (ConnectX-7 200G RoCE + dg5W/dg5R 호스트 + QSFP56 트랜시버)
  - **GUI 목업** (`mockup/index.html` 단일 HTML, ManyCore 로고 적용, 사용자 승인 완료)
- 코드(app/, frontend/) 미작성

---

## 결정 완료 사항

| # | 항목 | 결정 |
|---|------|------|
| 1 | 측정 도구·통신 방식 | 메인 `ib_write_bw` + `ib_read_lat` (RoCE/RDMA), 옵션 `iperf3` (TCP), `mock` (데모) |
| 2 | 백엔드 | FastAPI + asyncssh + structlog |
| 3 | 프론트 스택 | SvelteKit + Vite + Tailwind v4 + ECharts + GSAP + Lucide |
| 4 | 실시간 푸시 | SSE 단방향 (컨트롤은 일반 POST). 4 이벤트: `measurement` / `nic_temp` / `status` / `error` |
| 5 | 토폴로지 | 단일 controller (한 서버 겸함) + asyncssh로 양쪽 측정 트리거 |
| 6 | NIC | Mellanox **ConnectX-7 200G**, RoCE v2, MLNX_OFED 사전 설치 |
| 7 | UI 톤 | 흑백 + cyan(#00d9ff) 강조, KPI 72px 폰트, 모션은 GSAP 풀가속 |
| 8 | 양방향 모드 | UNI / BIDIR 토글 (perftest `-b`, iperf3 `--bidir`). 차트 Y축 200/400 동적 |
| 9 | NIC 텔레메트리 | 4채널 (IC × 2 서버 + Module × 2 서버), 1Hz 폴링, mget_temp + ethtool -m |
| 10 | 광 트랜시버 | **QSFP56**, Liquid-Cooled |
| 11 | 호스트 모델 | Server A = `dg5W-H200NVL-4`, Server B = `dg5R-PRO6000SE-10` |
| 12 | 냉각 | NIC IC + 광 트랜시버 모두 Liquid-Cooled (UI에 명시 표기) |
| 13 | 회사 로고 | ManyCore PNG (white/black 두 버전, mockup 적용 완료) |
| 14 | SSH 정책 | controller self-SSH 포함 모든 호출을 SSH로 통일 (subprocess 분기 X). known_hosts 사전 등록 |
| 15 | NIC 텔레메트리 권한 | 1차 sysfs hwmon (sudo 불필요), 2차 `mget_temp` sudoers NOPASSWD fallback |
| 16 | NIC 텔레메트리 SSH 풀 | 측정 SSH와 별도 connection — fault isolation |
| 17 | SSE 큐 정책 | 구독자별 `asyncio.Queue(maxsize=256)` + drop-oldest, 30분 idle timeout |
| 18 | 명명 규약 | `SessionStatus` (외부 응답 DTO) vs `SessionState` (내부 머신 상태값) 구분 |
| 19 | 정본 파일 매핑 | CLAUDE.md 상단 표에 카테고리별 단일 정본 명시 (drift 방지) |

상세 → 각 문서 참조.

---

## 결정 대기 항목 (Phase 1 이후 채울 것)

| 항목 | 영향 | 결정 시점 |
|------|------|----------|
| RDMA GID index 정확값 | `measurement.md` perftest `-x` 옵션 | Phase 1 시 `show_gids` 출력으로 확정 |
| 케이블 종류 세부 (DAC/AOC, 길이) | 운영 문서 | Phase 4 |
| 관리망 IP / RoCE 망 IP 분리 여부 | 운영 / 보안 | Phase 1 |
| MLNX_OFED 정확 버전 | 의존성 명시 | 설치 시 |
| 부스 디스플레이 해상도 (1080p / 4K) | 반응형 정책 | Phase 4 |
| 폰트 파일 (Inter / JetBrains Mono) | self-hosted 자산 | Phase 3 시작 시 |

---

## 다음 액션

1. ✅ **교차검증 1라운드 완료** — arch / impl / harness 3 reviewer 보고 + 피드백 반영 commit (CRITICAL 5건 + HIGH 7건 + 핵심 MEDIUM 4건)
2. **교차검증 2라운드** — 1라운드 피드백 반영본 재검토
3. 피드백 반영 PR #1 머지
4. **Phase 1 시작**: 브랜치 `feature/measurement-poc`
   - `app/schemas.py` (StartRequest, SessionStatus, MeasurementEvent, NicTelemetry — 정본 → rules/measurement.md)
   - `app/config.py` (Settings BaseSettings)
   - `app/parser.py` (ib_write_bw / ib_read_lat / iperf3 — uni + bidir 모두)
   - `app/runner.py` (asyncssh + mock_session)
   - `tests/conftest.py` + `tests/fixtures/` (BIDIR fixture 캡처 필수)
   - `scripts/poc.py` CLI
   - `.github/workflows/ci.yml` (Phase 2 진입 전에 추가)

---

## 미처리 이슈

없음 (Phase 0 진행 중, mockup 완료).

---

## 참고

- 인스펙션 시스템(`~/workspace/projects/inspection-system`)과는 인프라·코드 모두 별개
- 워크스페이스 룰 (`~/workspace/rules/*.md`)이 본 프로젝트 룰 위에 fallback으로 적용됨 (워크스페이스 worktree에서는 `~/workspace/.claude/worktrees/<name>/rules/`가 동일 내용)
- 본 프로젝트 룰이 워크스페이스 룰과 충돌 시 본 프로젝트 룰 우선 (워크스페이스 `CLAUDE.md` 규칙 우선순위)
- 호스트 모델 dg5W/dg5R 상세 스펙: `~/workspace/projects/inspection-system/context/target-servers.md`
