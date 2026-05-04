# UI/UX 사양

> 본 파일은 시각 디자인·인터랙션 사양. 코드 룰은 `.claude/rules/frontend.md` 참조.

## 1. 컨셉

**"200G RoCE의 raw performance를 무인 부스에서 시네마틱하게 보여준다."**

- 관람객이 한눈에 "지금 빠르게 통신 중이다"를 인지
- 수치는 직관적 (Gb/s, µs), 그래프는 역동적
- 흑백 + 강조색 1개로 절제된 고급감
- 무인 가동: 항상 켜져 있고, 시작/정지만으로 운용

## 2. 참고 사이트 분석

| 사이트 | 가져올 요소 | 안 가져올 요소 |
|-------|-----------|--------------|
| [awwwards Overwatch](https://www.awwwards.com/sites/overwatch) | 풀스크린 시네마틱 무드, scroll-driven hero, 강한 타이포그래피 | 게임 비주얼, 3D 캐릭터 |
| [nperf](https://www.nperf.com/ko/) | 큰 게이지 + 시계열 그래프 + 단계별 결과 카드 | 컬러풀 차트(우리 톤과 다름) |
| [cloudflare speed test](https://speed.cloudflare.com/) | 미니멀 + 큰 숫자 카운터 애니메이션 + 상태 단계화 | 라이트 테마 |
| [traceroute-online](https://traceroute-online.com/) | 네트워크 노드·라인 시각화, 흐름 애니메이션 | 지도/지리 정보 |

종합: **cloudflare 식 미니멀 카운터 + nperf 식 그래프 + traceroute 식 흐름 시각화 + Overwatch 식 시네마틱 톤**.

## 3. 색상 팔레트

| 토큰 | 값 | 용도 |
|------|-----|------|
| `bg` | `#0a0a0a` | 배경 (진한 검정) |
| `surface` | `#141414` | 카드·패널 배경 |
| `surface-2` | `#1c1c1c` | 호버·강조 패널 |
| `border` | `#262626` | 구분선 |
| `text` | `#ffffff` | 본문 텍스트 (기본 대비) |
| `text-2` | `#e5e5e5` | 보조 텍스트 |
| `muted` | `#a1a1aa` | 라벨·푸터 |
| `accent` | `#00d9ff` | 시안 강조 (BW 라인, 액티브 상태, glow) |
| `accent-2` | `#00aacc` | accent 보조 (그라디언트 끝) |
| `success` | `#22c55e` | RUNNING 배지 |
| `warning` | `#f59e0b` | 경고 |
| `danger` | `#ef4444` | ERROR 상태 |

특수 효과:
- **glow**: `box-shadow: 0 0 24px rgba(0, 217, 255, 0.4)` — 액티브 카드, 그래프 라인
- **gradient line**: `linear-gradient(90deg, accent 0%, transparent 100%)` — 패킷 흐름 페이드

## 4. 타이포그래피

| 용도 | 폰트 | 사이즈 |
|------|------|--------|
| 헤더 / 브랜드 | Inter Bold (또는 Geist) | 28px |
| 페이지 타이틀 | Inter Bold | 48px / 4xl |
| KPI 숫자 (메인) | **JetBrains Mono Bold** | **96px (5em+)** |
| KPI 단위 | JetBrains Mono Regular | 24px |
| KPI 라벨 | Inter Medium uppercase tracking-wider | 12px |
| 본문 | Inter Regular | 14px |
| 작은 푸터 | Inter Regular | 12px / muted 색 |

폰트는 self-hosted (`frontend/static/fonts/`). CDN 미사용.

## 5. 페이지 레이아웃

해상도 기준: **1920×1080 (1080p)** 최우선, **3840×2160 (4K)** 대응 (Tailwind `2xl:`).

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [회사 로고 SVG]   ·   P2P PERF MONITOR              ● RUNNING  10:42:13  │ HEADER  (h:72px)
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ┌──────────────────────┐ ┌─QSFP56─┐  ●●●●  ┌─QSFP56─┐ ┌──────────────────┐│ HARDWARE
│ │ dg5W-H200NVL-4       │ │ Liquid │ link  │ Liquid │ │ dg5R-PRO6000SE-10│ │ DIAGRAM
│ │ ◇ LIQUID-COOLED      │ │ MODULE │═══════│ MODULE │ │ ◇ LIQUID-COOLED  │ │ (h:280px)
│ │ [CPU][RAM][PCIe5x16] │ │  41°C  │       │  43°C  │ │[CPU][RAM][PCIe5] │ │
│ │ ConnectX-7 · mlx5_0  │ └────────┘       └────────┘ │ConnectX-7·mlx5_0 │ │ packet flow
│ │ IC TEMP        62°C  │                              │ IC TEMP    64°C  │ │ animation
│ └──────────────────────┘                              └──────────────────┘ │
│                                                                          │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ KPI CARDS
│   │             │ │             │ │             │ │             │       │ (h:240px)
│   │   187.4     │ │   175.2     │ │   198.5     │ │    1.8      │       │
│   │             │ │             │ │             │ │             │       │
│   │   Gb/s      │ │   Gb/s      │ │   Gb/s      │ │    µs       │       │
│   │   NOW       │ │   AVG       │ │   PEAK      │ │   LATENCY   │       │
│   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                          │
│   ┌──────────────────────────────────────────┐  ┌─[NIC IC & MODULE]─┐  │ MAIN CHARTS
│   │ Bandwidth (Gb/s)                  ● live  │  │ ┌IC·A┐ ┌IC·B┐    │  │ left: BW
│   │  200 ┤                                     │  │ │62.4│ │64.1│    │  │ right: 4 tiles
│   │  150 ┤      ╱╲    ╱╲╱╲      ╱╲╱╲╱╲        │  │ └────┘ └────┘    │  │  + 4-line
│   │  100 ┤  ╱╲╱╲  ╲╱╲╱    ╲╱╲╱╲╱              │  │ ┌MOD·A┐┌MOD·B┐   │  │  timeseries
│   │   50 ┤                                     │  │ │41.5││43.0│    │  │ (IC solid,
│   │    0 └─────────────────────────           │  │ └────┘ └────┘    │  │  Module dashed)
│   │      0s    10s    20s    30s    40s   60s │  │ ────── 4 lines ──│  │
│   └──────────────────────────────────────────┘  └──────────────────┘  │
│                                                                          │
│   ┌─[ TOOL ▾ ]─[ MSG SIZE ▾ ]─[ DURATION ▾ ]─[ DIR ▾ ]──[ ▶ START ]─┐  │ CONTROL
│   └───────────────────────────────────────────────────────────────┘     │ (h:80px)
├─────────────────────────────────────────────────────────────────────────┤
│ NIC mlx5_0 · MLNX_OFED 24.10 · RoCE v2 · MTU 9000           v0.1   ©   │ FOOTER  (h:32px)
└─────────────────────────────────────────────────────────────────────────┘
```

영역 비율 (1080p 기준):
- HEADER 72px + FOOTER 32px = 104px 고정
- 잔여 ≈ 976px 분할: HARDWARE 280px / KPI 200px / CHART 1fr (≈324px) / CONTROL 72px / gaps·여백 100px

KPI 카드 폰트: 72px (이전 88px에서 축소 — HARDWARE 영역 확대분 보전)
4K 환경: 폰트·박스 1.5×, 차트 영역 비례 확대

## 6. 컴포넌트 사양

### 6.1 Header

- 좌: **회사 로고 이미지(SVG, height 40px)** + 구분점 "·" + "P2P PERF MONITOR" 텍스트
  - 로고 자산 위치: `frontend/static/logo.svg` (실제 파일 받기 전까지는 `mockup/logo.svg` 의 placeholder 사용)
  - 텍스트(DEEPGADGET 등)는 로고 이미지 안에 포함되므로 별도 워드마크 표시 안 함
- 우: 상태 배지 (StatusBadge) + 현재 시각 (mono, hh:mm:ss)
- 높이: 72px (로고 + 여백)
- 배경: bg, 하단 1px border

### 6.2 StatusBadge

상태 4종:
| 상태 | 색 | 아이콘 | 텍스트 | 효과 |
|------|---|-------|-------|------|
| IDLE | muted | ● | IDLE | 정적 |
| RUNNING | accent | ● | RUNNING | **pulse glow 1.2s** |
| ERROR | danger | ● | ERROR | 정적 + 텍스트 hover로 메시지 |
| CONNECTING | warning | spinner | CONNECTING | 회전 |

### 6.3 HardwareDiagram

크기: 영역 height 280px (1080p 기준 — 작아 보이지 않게 충분히 크게). SVG viewBox `0 0 1820 280`, 컨테이너에 가깝게 가득 차도록 비율 조정.

요소:
- **서버 박스 2개** (좌·우, 각 540×240px) — surface 배경, border, 내부에 CPU/RAM/PCIe 박스
- **서버 라벨** (박스 상단, 22px Bold mono):
  - 좌: `dg5W-H200NVL-4`
  - 우: `dg5R-PRO6000SE-10`
- **LIQUID-COOLED 태그** (서버 라벨 바로 아래, 11px tracking-wider, accent ◇ 아이콘): 서버 자체가 액냉 시스템임을 명시
- **NIC indicator 박스** (각 서버 박스 안): "ConnectX-7 · mlx5_0" 라벨 (16px accent)
- **NIC IC TEMP row** (NIC 박스 아래): "IC TEMP" 태그 + 18px 굵은 값 + "°C" — 1Hz 갱신
- **광 트랜시버 박스 2개** (두 서버 사이): 각 160×100px
  - "QSFP56" 라벨 + "OPTICAL · LIQUID-COOLED" 서브라벨
  - "MODULE" 태그 + 14px 굵은 값
- **연결 라인 모드**:
  - 단방향 (UNI): 트랜시버 사이 1줄 (y=170)
  - 양방향 (BIDIR): 2줄 (y=160, y=180), 위 좌→우 / 아래 우→좌
- **NIC ↔ Transceiver 짧은 stub 라인**: 항상 표시
- **패킷 흐름 dot**: 트랜시버 사이 (x: 800 → 1020) cyan dot 5개 stagger 흐름

색상 코딩 (NIC IC overlay + Transceiver Module overlay 공통):
- IC: < 75°C cyan / 75~85 amber / ≥85 red
- Module: < 65°C cyan / 65~75 amber / ≥75 red (트랜시버 한계가 더 낮음)
- **연결 라인 모드**:
  - **UNI (단방향)**: 1줄 라인 (중앙 y=115). 좌→우 dot 흐름
  - **BIDIR (양방향)**: 2줄 라인 (위 y=105, 아래 y=125). 위는 좌→우, 아래는 우→좌, dot 동시 흐름
  - 모드 전환은 `ControlPanel`의 DIRECTION 토글 (§6.6)에 연동
  - 라벨("200G RoCE v2 · MTU 9000") 위치도 모드에 맞게 이동 (UNI: y=100, BIDIR: y=85)
- **패킷 흐름**: 라인 위에 cyan dot (지름 8px, glow) 반복 이동
  - GSAP timeline, 속도 = `bw_avg_gbps`에 비례
  - 단방향: 6 dots 좌→우 stagger
  - 양방향: 위 라인 6 dots(좌→우) + 아래 라인 6 dots(우→좌) — 아래는 0.125s offset으로 시각적 분리
  - IDLE 상태: dot 미표시
  - RUNNING: 정상 속도
  - peak 근접 시: dot 글로우 강화 + 잔상 라인 추가

레이어:
1. 정적 다이어그램 (서버 박스 + 라인 + 라벨)
2. 흐름 dot 레이어 (GSAP 제어)
3. (옵션, Phase 4) Threlte 3D 모드 토글

### 6.4 KpiCards

4개 카드: NOW / AVG / PEAK / LATENCY

각 카드:
- 배경: surface, border, rounded-2xl
- 패딩: 32px
- 레이아웃: 라벨(상단) + 숫자(중앙 거대) + 단위(하단 작게)
- 숫자 폰트: JetBrains Mono Bold 88~96px, color text
- 단위: JetBrains Mono 22~24px, color muted
- **라벨 강조**: Inter 13px **Bold**, uppercase, tracking 0.18em, color text-2 (밝게)
  - 좌측에 4×14px accent 컬러 bar(둥근 사각형, 글로우) 부착해서 시각적 강조
  - "라벨이 묻히는" 인상을 피하고 카드의 의미를 빠르게 인지하도록 함

업데이트 모션:
- 신규 값 도착 시 GSAP `to(value, 0.4s, "power2.out")` 카운터 트윈
- 200G NIC peak 95% 이상 도달 시 카드에 잠시 accent border + glow (0.6s)
- ERROR 상태: 숫자 dim + "─" 표시

### 6.4-bis NicTempPanel

차트 영역을 좌우 분할(2fr : 1fr): 좌측 BandwidthChart, 우측 NicTempPanel.

NicTempPanel 내부:
1. 헤더: "NIC IC & MODULE TEMPERATURE" 라벨 + LIVE 인디케이터
2. **4 타일 (2×2 grid)**:
   - 1행: `IC · SERVER A`, `IC · SERVER B` (solid 좌측 사이드바)
   - 2행: `MODULE · SERVER A`, `MODULE · SERVER B` (dashed 좌측 사이드바 — IC와 시각 구분)
   - 각 타일: JetBrains Mono 28px 굵은 숫자 + "°C" 단위
   - 색상 코딩은 컴포넌트별 임계값(§6.3) 따름
3. **시계열 미니 차트 (ECharts) — 4개 라인**:
   - `IC A`: cyan solid
   - `IC B`: amber solid
   - `MOD A`: cyan dashed
   - `MOD B`: amber dashed
   - 색은 서버 구분(A=cyan, B=amber), 선 스타일은 컴포넌트 구분(IC=solid, Module=dashed)
   - Y축: 25 ~ 90°C
   - 범례: 우상단 작게 (4개 항목)
   - X축: BW 차트와 동일한 elapsed time

타일 색상 코딩 표시:
| 컴포넌트 | 정상 | 경고 | 위험 |
|---------|------|------|------|
| IC | < 75°C cyan | 75~85°C amber + 카드 글로우 | ≥85°C red + 강한 글로우 |
| Module | < 65°C cyan | 65~75°C amber + 카드 글로우 | ≥75°C red + 강한 글로우 |
| 측정 실패 | "—°C" muted | | |

폴링: 1Hz로 항상 동작 (idle/running 무관). 측정 중에는 시계열에 누적 push, IDLE에선 카드만 갱신.

데이터 소스 → `.claude/rules/measurement.md` "NIC IC + 광 모듈 온도 텔레메트리" 섹션 + SSE `event: nic_temp` (4 채널)

### 6.5 BandwidthChart

ECharts line chart.
- 데이터: 최근 600 포인트 (60s @ 10Hz)
- X축: 상대 시간 ("0s", "10s", ..., "60s"). label 색 muted
- Y축: 0 ~ 200 Gb/s 고정 (NIC 이론 최대 기준)
- 라인 색: accent. 두께 2.5px
- 라인 아래 영역: linear-gradient(top: accent 30% opacity → bottom: transparent)
- 격자: 매우 옅게 (`#1c1c1c`)
- 마우스 hover: tooltip on (시각 + 값)
- 측정 시작 시 GSAP으로 chart container fade-in (0.5s) + 첫 라인 stroke-dasharray 진행

### 6.6 ControlPanel

```
[ TOOL: ib_write_bw ▾ ] [ MSG SIZE: 64K ▾ ] [ DURATION: 60s ▾ ] [ DIRECTION: UNI ▾ ]   [ ▶ START ]
```

- TOOL: dropdown — `ib_write_bw` / `ib_read_lat` / `iperf3` / `mock`
- MSG SIZE: dropdown — 64 / 1K / 8K / 64K / 256K / 1M (perftest 한정. iperf3 선택 시 회색)
- DURATION: dropdown — 30s / 60s / 120s / 300s
- **DIRECTION**: dropdown — `UNI` / `BIDIR`
  - `BIDIR`: 양방향 동시 측정 (perftest `-b`, iperf3 `--bidir`). BW 합산값 표시
  - `ib_read_lat` 선택 시 `BIDIR`은 회색 (latency 양방향 무의미)
  - 모드 전환 시 HardwareDiagram 라인 1줄↔2줄 전환, 차트 Y축 max 200↔400 동적 조정
- START 버튼: 큰 버튼 (right), accent 배경 → 흰 텍스트, 마우스 hover glow
  - RUNNING 상태에선 "■ STOP" (danger 배경)으로 변환
- 모든 컨트롤 disabled 시: opacity 50%

### 6.7 Footer

- NIC 디바이스 (`mlx5_0`)
- MLNX_OFED 버전
- RoCE 버전 (`v2`)
- MTU
- 우측: `v0.1` + © 회사

작은 muted 텍스트, 호스트명/IP는 표시하지 않음 (보안 → `.claude/rules/security.md`).

## 7. 모션 사양 (GSAP timelines)

### 7.1 Initial Page Load

```
0.0s: 화면 검정 페이드인
0.2s: Header 위에서 슬라이드 (y: -20 → 0)
0.4s: HardwareDiagram 좌우 서버 박스 동시 슬라이드 (좌: x: -40 → 0, 우: x: +40 → 0)
0.7s: 두 NIC 사이 라인 stroke-dasharray로 좌→우 그리기 (0.5s)
1.2s: KpiCards 4개 stagger fade-up (각 0.1s 간격)
1.6s: BandwidthChart fade-in
1.8s: ControlPanel 아래에서 슬라이드 (y: +20 → 0)
```

### 7.2 START 버튼 클릭

```
0.0s: 버튼 ripple (scale 1 → 0.95 → 1, 0.2s)
0.1s: API POST /api/start
0.3s: 상태 IDLE → CONNECTING (배지 회전)
0.5~1.5s: SSH 연결 + 측정 시작 대기
0.0s (status=RUNNING 수신 시):
  - 배지 RUNNING + pulse glow 시작
  - HardwareDiagram 라인 위 dot stream 등장 (stagger 5개)
  - KpiCards 카운터 0 → 첫 값 (0.4s ease-out)
  - BandwidthChart 첫 데이터 포인트 추가, 진입 효과
```

### 7.3 STOP / 종료

```
0.0s: dot stream fade-out (0.3s)
0.2s: KpiCards "─" 처리 (또는 마지막 값 dim)
0.4s: 상태 RUNNING → IDLE
0.5s: ControlPanel "▶ START" 복귀
```

### 7.4 ERROR

```
0.0s: 배지 RUNNING → ERROR (danger 색 fade)
0.0s: 화면 좌상단 toast (error message tail) 슬라이드 인
0.0s: HardwareDiagram dot stream 즉시 fade-out
0.0s: KpiCards 마지막 값 유지하되 dim (opacity 0.5)
5.0s: toast auto fade-out
```

### 7.5 Peak 도달 (NIC 이론치 95%)

임계값:
- UNI: `bw_avg_gbps >= 195`
- BIDIR: `bw_avg_gbps >= 380`

```
임계값 5회 연속 도달 시:
  - HardwareDiagram dot stream 가속 + 잔상 라인 + glow 강화
  - KpiCards "NOW" 카드 accent border + glow pulse 1회 (0.6s)
  - 화면 외곽에 미세한 cyan vignette (0.4s on/off)
이 효과는 무인 시연 중 임팩트 강조용. 5초 이상 연속되면 자동 reset
```

## 8. 인터랙션

- **마우스 모든 인터랙션 옵션**: 부스 디스플레이는 보통 무인 + 키오스크. 마우스가 있다면 컨트롤만 사용
- **키보드**: ESC = STOP. SPACE = START/STOP toggle (관람객이 만지지 않게 비활성 옵션 가능)
- **터치**: 미지원 (1080p 부스 디스플레이 가정)
- **자동 리스타트**: 측정 종료 후 30초 idle → 자동 재시작 (옵션, kiosk 모드)

## 9. 반응형

| 해상도 | 정책 |
|--------|------|
| ≥ 3840×2160 (4K) | 폰트 1.5×, 카드 폰트 144px, 차트 확대 |
| 1920×1080 | 기본 |
| < 1920 | 비대응 (전시 부스 외) — 경고 메시지 표시 |
| 모바일 | 비대응 |

## 10. 데모 모드 시각 표시

- `tool=mock` 측정 중에는 푸터에 작은 텍스트 `DEMO MODE` (warning 색)
- 운영 환경에서 실수로 mock 사용 시 즉시 인지 가능

## 11. 접근성 / 무인 가동

- 자동 색상 대비 4.5:1 이상 (text vs bg, accent vs bg 모두 통과)
- 모션 멈춤 옵션: `prefers-reduced-motion` 미디어 쿼리 대응
  - dot stream → 정적 라인
  - KPI 카운터 → 즉시 갱신
- 화면 보호 끔: 운영 시 OS 화면 보호 비활성 + power-save 끔

## 12. 자산

| 자산 | 위치 | 비고 |
|------|------|------|
| 회사 로고 SVG | `frontend/static/logo.svg` | 흰/검 두 버전 (다크 배경용 흰색) |
| 폰트 | `frontend/static/fonts/` | Inter, JetBrains Mono — self-hosted |
| 아이콘 | Lucide Svelte | 컴포넌트로 import |

## 13. 검증

- 디자인 1차 검증: `frontend/` 정적 목업 (실 SSE 없이 mock 데이터)
- 2차 검증: `tool=mock` 백엔드 + SvelteKit dev 서버 통합
- 최종 검증: 실 200G NIC 환경 측정 + 부스 1080p 디스플레이
