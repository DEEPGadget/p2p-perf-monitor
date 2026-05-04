# 코드 스타일

## Python

- 도구: `ruff` (lint + format), `pytest`, `uv` (의존성 관리자)
- ruff 설정: `line-length = 100`, target = `py312`
- type hint 필수. `str | None` 사용 (`Optional[str]` 금지)
- f-string 사용 (`.format()`, `%` 금지)
- 구체 예외 catch. bare `except` 금지. 에러 메시지에 컨텍스트 포함
- import 순서: stdlib → 3rd-party → local. 그룹 사이 빈 줄
- async: API 핸들러·SSH·SSE는 async, parser·계산은 sync
- dict 키 접근: `dict.get(k, default)` 또는 명시적 KeyError 처리

## JavaScript (vanilla)

- 도구·빌드 시스템 없음. ES2022 직접 작성
- `const` 우선, 변경 필요 시만 `let`. `var` 금지
- 모듈 스코프: `<script type="module">`
- DOM 조작: `document.querySelector` / `getElementById`. jQuery 금지
- 비동기: `async/await` + `EventSource` (SSE). Promise chain 금지
- 의존성: vendored (`static/vendor/chart.min.js`). npm 사용 안 함

## 의존성 관리

- Python: `pyproject.toml` `[project] dependencies` 에 직접 명시. `uv add` 로 추가
- 신규 외부 의존성 도입 시 PR 본문에 사유 명시
- 프론트 라이브러리: `static/vendor/`에 직접 복사 (CDN 금지 — 폐쇄망 동작 보장)

## 파일 명명

- Python 모듈: `snake_case.py`
- 정적 자산: `kebab-case.css/js`
- 테스트: `tests/test_<module>.py`

## 주석 정책

- WHY가 비자명한 곳에만. WHAT은 식별자로 표현
- TODO 주석: `# TODO(<github_issue_or_pr>): ...` 형식. 주인 명시
