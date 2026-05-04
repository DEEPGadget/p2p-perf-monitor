# Handoff — p2p-perf-monitor

> 최종 업데이트: 2026-05-04
> 이 파일의 범위: **다음 작업 + 결정 대기 항목 + 블로커**. 아키텍처·구현 현황 → 프로젝트 `CLAUDE.md`

---

## 추천 시작점

**다음 작업**: 결정 대기 항목 6건 사용자와 합의 → 그 결과를 `CLAUDE.md` Architecture/Directory 섹션에 반영 → 첫 PoC 코드 작성

**현재 상태**:
- repo 초기 골격만 존재 (README / CLAUDE / handoff / .gitignore)
- `main` 빈 상태 (초기 커밋만)
- 기술 스택·측정 방식 모두 미정

---

## 결정 대기 항목 (작업 시작 전 반드시 합의)

| # | 항목 | 후보 | 비고 |
|---|------|------|------|
| 1 | 측정 도구·통신 방식 | RoCE/IB RDMA(`perftest`) / TCP(`iperf3`) / GPUDirect(`nccl-tests`) / 자체 | NIC 모델·드라이버에 의존 |
| 2 | 백엔드 | FastAPI(Python) / Node.js / Go | RDMA 라이브러리 바인딩 가능성 고려 |
| 3 | 프론트 | React / Vue / Svelte / SvelteKit | 전시 UI 단순함 우선 |
| 4 | 실시간 푸시 | WebSocket / SSE | 단방향 충분 시 SSE |
| 5 | 수집 토폴로지 | (A) 한 서버에 웹+수집 / (B) 각 서버 agent + collector | 운영·부팅 단순성 vs 확장성 |
| 6 | NIC 모델·드라이버 | TBD | OFED/MLNX_OFED 사전 설치 여부 |

---

## 다음 액션

1. 위 6항목 사용자와 합의 (대화 1~2턴)
2. `CLAUDE.md` Architecture / Directory / Commands 섹션 채우기
3. PoC: 한쪽 서버에서 측정 도구 호출 → JSON 출력 파싱 → 표준출력 확인
4. PoC 검증 후 백엔드 → 프론트 순으로 골격 추가
5. 첫 PR 생성

---

## 환경 메모

전시 환경 = 서버 2대 + NIC 1장씩. 검수 시스템(`inspection-system`)과는 별개 인프라.
구체 IP·NIC 모델은 결정 후 `context/`에 추가 예정.

---

## 미처리 이슈

없음 (초기 단계).
