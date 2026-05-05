// SSR 비활성화 — 시연용 SPA. ECharts/GSAP 등 client-only 의존성 회피.
// adapter-static 의 fallback index.html 은 prerender 가 만들어줌.
export const ssr = false;
export const prerender = true;
