# 프론트엔드 규칙

## 기술 스택

- **SvelteKit** (Svelte 5, runes API: `$state`, `$derived`, `$effect`)
- **Vite** (SvelteKit 내장)
- **TypeScript** (strict mode)
- **Tailwind CSS v4**
- **ECharts v5** (시계열 그래프)
- **GSAP v3** (모션·카운터)
- **Lucide Svelte** (아이콘)
- **adapter-static** (정적 빌드 → FastAPI 서빙)
- (옵션) **Threlte** (3D 하드웨어 구성도, Phase 4 이후 검토)

빌드 결과: `frontend/build/` → FastAPI `StaticFiles(directory="frontend/build")`로 서빙.

## 디렉터리 구조

전체 디렉터리 트리는 정본 → `CLAUDE.md` §Directory.

본 룰은 **`lib/` 하위 코드 작성 컨벤션**만 다룸:
- `lib/components/<PascalCase>.svelte` — UI 컴포넌트, Svelte 5 runes
- `lib/stores/<name>.svelte.ts` — runes 기반 store
- `lib/utils/<name>.ts` — 순수 함수 / 인프라 (SSE, format, api)
- `lib/types/api.ts` — 백엔드 Pydantic 모델 1:1 TS 타입

## 코드 룰

### Svelte

- **Svelte 5 runes** 사용. `$state`, `$derived`, `$effect`, `$props`
- 레거시 reactive `$:` 문법 금지
- 컴포넌트당 하나의 책임. 100라인 초과 시 분할 검토
- props는 TypeScript 타입 명시: `let { value }: Props = $props()`
- 이벤트는 callback prop 패턴 (Svelte 5 권장). `createEventDispatcher` 사용 안 함

### TypeScript

- strict mode 항상 ON
- `any` 금지. 불가피하면 `unknown` + narrowing
- DTO는 `lib/types/api.ts`에 백엔드 Pydantic 모델과 1:1 매칭

### Tailwind

- 디자인 토큰 정본 → `docs/ui-ux-spec.md` §3 색상 팔레트
- `tailwind.config.js`에는 정본의 모든 토큰을 1:1 등록 (현재: `bg`, `surface`, `surface-2`, `border`, `text`, `text-2`, `muted`, `accent`, `accent-2`, `success`, `warning`, `danger`)
- 인라인 임의값(`text-[#abc123]`) 사용 금지. 토큰만 사용
- 컴포넌트별 `<style>` 블록은 Tailwind로 표현 어려운 효과(드롭섀도우 글로우 등)에만

### 모션 (GSAP)

- 화면 전환·카운터·복합 타임라인은 GSAP
- 단순 hover/transition은 Tailwind `transition-*`
- 모든 GSAP 애니메이션은 컴포넌트 unmount 시 cleanup (`onDestroy(() => tl.kill())`)
- 60fps 유지: 동시 active timeline ≤ 5

### ECharts

- 인스턴스는 컴포넌트당 1개. `onMount`에서 `init`, `onDestroy`에서 `dispose`
- 데이터 업데이트는 `setOption({...}, { lazyUpdate: true })`
- 데이터 포인트 보관 ≤ 600개 (60초 @ 10Hz). 초과분 shift
- `animation: false` (실시간성 우선). 라인 진입 효과는 GSAP로 별도 구현
- 색상은 Tailwind 토큰을 CSS 변수로 노출 후 ECharts에서 참조

## SSE 구독 (`lib/utils/sse.ts`)

- `/api/stream` 단일 채널, **4종 이벤트** (`measurement` / `nic_temp` / `status` / `error`)
- 각 이벤트는 별도 store에 dispatch (measurement / nic_telemetry / session)
- EventSource 자동 재연결 사용
- 발행 주기·payload 정의 → `.claude/rules/api.md` §SSE 포맷
- store 구독자 0 시 `es.close()`

구체 구현은 `lib/utils/sse.ts`. 본 룰은 인터페이스만 명시(코드 예시는 stale 위험 회피).

## 빌드 & 정적 서빙

- `svelte.config.js`:
  ```js
  import adapter from '@sveltejs/adapter-static'
  export default {
    kit: {
      adapter: adapter({ pages: 'build', fallback: 'index.html' }),
      prerender: { handleHttpError: 'warn' }
    }
  }
  ```
- 운영: `pnpm build` → FastAPI가 `/`에 마운트, `/api/*`는 라우터로 라우팅

## 금지 항목

- 외부 CDN (Google Fonts 포함) — 폐쇄망 동작 보장
- `innerHTML`로 사용자 입력 삽입 (XSS 방지: `textContent` 또는 Svelte 자동 escape)
- `any` 타입
- 인라인 hex 색상 (Tailwind 토큰만)
- jQuery, Bootstrap, Material UI 등 무거운 프레임워크
- npm postinstall 훅으로 외부 다운로드

## 데모 모드

`/api/start` body `tool="mock"` 호출 시 백엔드가 mock generator로 SSE 발행 → 동일 UI로 검증.
별도 frontend 데모 모드 플래그 불필요.

## 디자인 사양 위임

페이지 레이아웃, 색상 팔레트, 모션 timeline, KPI 카드 사양 등 시각 디자인은 → `docs/ui-ux-spec.md`.
본 파일은 코드 작성 룰에 한정.
