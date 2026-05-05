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
  - `context/nic-environment.md` (ConnectX-6 200G RoCE + dg5W/dg5R 호스트 + QSFP56 트랜시버)
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
| 6 | NIC | Mellanox **ConnectX-6 200G**, RoCE v2, MLNX_OFED 사전 설치 |
| 7 | UI 톤 | 흑백 + cyan(#00d9ff) 강조, KPI 72px 폰트, 모션은 GSAP 풀가속 |
| 8 | 양방향 모드 | UNI / BIDIR 토글 (perftest `-b`, iperf3 `--bidir`). 차트 Y축 200/400 동적 |
| 9 | NIC 텔레메트리 | 4채널 (IC × 2 서버 + Module × 2 서버), 1Hz 폴링, mget_temp + ethtool -m |
| 10 | 광 트랜시버 | **QSFP56**, Liquid-Cooled |
| 11 | 호스트 모델 | Server A = `dg5W-H200NVL-4`, Server B = `dg5R-PRO6000SE-8` |
| 12 | 냉각 | NIC IC + 광 트랜시버 모두 Liquid-Cooled (UI에 명시 표기) |
| 13 | 회사 로고 | ManyCore PNG (white/black 두 버전, mockup 적용 완료) |
| 14 | SSH 정책 | controller self-SSH 포함 모든 호출을 SSH로 통일 (subprocess 분기 X). known_hosts 사전 등록 |
| 15 | NIC 텔레메트리 권한 | 1차 sysfs hwmon (sudo 불필요), 2차 `mget_temp` sudoers NOPASSWD fallback |
| 16 | NIC 텔레메트리 SSH 풀 | 측정 SSH와 별도 connection — fault isolation |
| 17 | SSE 큐 정책 | 구독자별 `asyncio.Queue(maxsize=256)` + drop-oldest, 30분 idle timeout |
| 18 | 명명 규약 | `SessionStatus` (외부 응답 DTO) vs `SessionState` (내부 머신 상태값) 구분 |
| 19 | 정본 파일 매핑 | CLAUDE.md 상단 표에 카테고리별 단일 정본 명시 (drift 방지) |
| 20 | NIC 포트 구성 | 2-port ConnectX-6. **1-port만 사용** (PCIe Gen5 x16 단방향 ~256G 한도, 1-port + BIDIR이 시연 임팩트 최대). 양쪽 서버 동일 포트 |
| 21 | UI 다이어그램 표기 | 단일 NIC 박스 (미사용 포트 표시 안 함, 가독성 우선) |
| 22 | 패키징 | **Docker Compose** 채택 (multi-stage Dockerfile, single 컨테이너, systemd wrapper) |
| 23 | 네트워크 분리 | 관리망(SSH, 192.168.1.x) + RDMA 망(perftest 인자, 25.47.1.x) 별도. ENV `SERVER_{A,B}_HOST` (SSH IP) + `SERVER_{A,B}_RDMA_IP` (RDMA IP) |
| 24 | 호스트 IP | dg5W: SSH `192.168.1.166` / RDMA `25.47.1.10` / netdev `enp2s0f0np0`. dg5R: SSH `192.168.1.204` / RDMA `25.47.1.11` / netdev `ens7f0np0` |
| 25 | SSH 초기 setup | install.sh 가 PW(deepgadget)로 ssh-copy-id 1회 → 키 인증 전환. .env 에는 PW 저장 X |
| 26 | IB → RoCE 전환 완료 | 양쪽 서버 link layer Ethernet, RoCE v2 활성. 인터페이스명 `ib*` → `enp*`/`ens*` |
| 27 | **NIC 실제 모델 ConnectX-6** | 라이브 검증으로 ConnectX-7 가정 정정. PCI 15B3:101B (MT28908). 200G HDR, RoCE v2 |
| 28 | RDMA device 명명 비대칭 | dg5W=`mlx5_0` (전통), dg5R=`rocep100s0f0` (udev `roce p<bus_dec>s<slot>f<func>`). driver 양쪽 mlx5_core 동일 |
| 29 | MTU 정책 | **9000 (Jumbo) 권장**. 라이브 첫 측정 시 1024로 ~181 Gb/s. 9000 적용 후 195+ 예상 |
| 30 | 측정 흐름 재설계 | perftest stdout 이 종료 시 1줄만 출력 → 실시간 시각화 불가. **부하(perftest) + 측정(sysfs `tx_bytes`/`rx_bytes` 5Hz 폴링) 분리** |
| 31 | 라이브 검증 1차 | 2026-05-05: SSH 양쪽 OK, ib_write_bw 5초 측정 BW 평균 **181.32 Gb/s** (MTU 1024) |

상세 → 각 문서 참조.

---

## 결정 대기 항목 (Phase 1 이후 채울 것)

| 항목 | 영향 | 결정 시점 |
|------|------|----------|
| **MTU 9000 적용 + 재측정** | 200G 라인 레이트 도달 검증 | 사용자 환경 작업 + 재측정 |
| 케이블 종류 세부 (DAC/AOC, 길이) | 운영 문서 | Phase 4 |
| MLNX_OFED 정확 버전 | 의존성 명시 | 설치 시 |
| 부스 디스플레이 해상도 (1080p / 4K) | 반응형 정책 | Phase 4 |
| 폰트 파일 (Inter / JetBrains Mono) | self-hosted 자산 | Phase 3 시작 시 |

---

## 다음 액션

1. ✅ **교차검증 1라운드 완료** — arch / impl / harness 3 reviewer 보고 + 피드백 반영 commit (CRITICAL 5건 + HIGH 7건 + 핵심 MEDIUM 4건)
2. **교차검증 2라운드** — 1라운드 피드백 반영본 재검토
3. ✅ PR #1 머지 (Phase 0)
4. ✅ PR #2 머지 (2-port NIC 명시)
5. ✅ PR #3 머지 (네트워크 분리 + Docker 패키징)
6. ✅ **Phase 1 PoC 작성 완료** (브랜치 `feature/measurement-poc`, 4 commits)
   - `pyproject.toml` (uv + ruff + pytest)
   - `app/{__init__,schemas,config,parser,runner}.py`
   - `tests/{conftest,test_schemas,test_parser,test_runner}.py`
   - `tests/fixtures/` 6종 (perftest uni/bidir/lat 합성 + iperf3 3종)
   - `scripts/poc.py` CLI (--tool mock|ib_write_bw|ib_read_lat|iperf3)
7. **다음**: Phase 1 PR 머지 — 사용자 환경에서 `uv sync` + `pytest tests/ -m "not live"` 검증 후 머지
8. **(라이브 검증, 옵션)** RoCE 전환 + 인터페이스명 받은 후 실 NIC 환경에서 `pytest -m live` + `python scripts/poc.py --tool ib_write_bw --duration 30` 1회 검증, fixture 보강
9. ✅ Phase 2 머지 (PR #7) — FastAPI + SSE + sensors -j 텔레메트리
10. ✅ Phase 3 SvelteKit 프론트 (`feature/frontend-svelte`):
    - 7 components (Header, StatusBadge, HardwareDiagram, KpiCards, BandwidthChart, NicTempPanel, ControlPanel)
    - 3 stores (Svelte 5 runes), utils (sse/api/format), types (api.ts 백엔드 1:1)
    - `frontend/static/manycore_logo_*.png` mockup→frontend 이동
    - `app/main.py` StaticFiles 마운트로 `/` 정적 서빙
    - 빌드 6.88s, 통합 검증 (`/` index + 로고 + `/api/*` 모두 OK)
11. **다음**: Phase 4 — Docker Compose + systemd + install.sh

---

## 미처리 이슈

- BIDIR perftest stdout 포맷 미검증 (현재 합산 단일 라인 가정). RoCE 전환 후 실측 fixture 캡처로 보강
- iperf3 msg_size 필드 default 131072 (실제 -l 옵션 측정값과 일치 여부 확인 필요)

---

## 참고

- 인스펙션 시스템(`~/workspace/projects/inspection-system`)과는 인프라·코드 모두 별개
- 워크스페이스 룰 (`~/workspace/rules/*.md`)이 본 프로젝트 룰 위에 fallback으로 적용됨 (워크스페이스 worktree에서는 `~/workspace/.claude/worktrees/<name>/rules/`가 동일 내용)
- 본 프로젝트 룰이 워크스페이스 룰과 충돌 시 본 프로젝트 룰 우선 (워크스페이스 `CLAUDE.md` 규칙 우선순위)
- 호스트 모델 dg5W/dg5R 상세 스펙: `~/workspace/projects/inspection-system/context/target-servers.md`
