# 확인된 해결법

새 항목은 맨 아래에 추가한다. 형식: 막힘 → 해결법 → 근거(날짜·출처). 오래된 항목은 쓰기 전에 다시 확인한다.

## Claude Code 웹 검색 세션 한도

- **막힘:** `Web search was not performed: this session has used its web search budget (200 of 200 WebSearch calls)`
- **관찰(2026-09-23):** 기본 200회. 이 세션에서는 서브에이전트 6명과 메인이 한도를 함께 썼다(문서에는 각자 한도라는 설명이 있다는데 실제 동작은 공유였다 — 다시 확인할 것)
- **해결:** `~/.claude/settings.json`의 `env`에 `"CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION": "1000"` → 재시작 후 적용. 새 세션·`/clear`로도 초기화된다(claude-code-guide 답변 기준, `/compact`·`--resume`은 이어 셈)
- **비용:** 한도는 천장일 뿐 비용이 아니다. API 키 사용 시 검색 1,000회당 $10 + 토큰, 구독(Pro/Max) 로그인 시 건별 청구 없이 구독 사용량에서 처리(초과 사용을 켠 경우만 추가 결제). 출처: https://platform.claude.com/docs/en/about-claude/pricing (2026-09-23 확인)
- **한도와 무관하게 되는 것:** WebFetch(추가 요금 없음, 토큰만), `claude-in-chrome`으로 Google 검색

## 검색 엔진을 WebFetch로 여는 방법

- DuckDuckGo HTML: CAPTCHA가 뜬다 → **쓰지 않는다**(2026-09-23)
- Bing: 열리지만 한국어 검색 결과가 엉뚱하다(2026-09-23)
- 대신 공식 문서의 `llms.txt` → 해당 페이지를 WebFetch로 읽는 방식이 잘 된다(예: https://docs.aside.com/llms.txt)

## 로그인이 필요한 출처(네이버 카페, 커뮤니티 등)

- 조사원이 "로그인 필요 출처"로 목록을 남기게 하고, 메인이 사용자에게 로그인을 요청한 뒤 `claude-in-chrome`으로 읽는다(비밀번호는 입력하지 않는다)
- 대안 제품: **Aside** — 로그인한 사이트에서 대신 일하는 AI 브라우저(YC F25, 한국 팀). Chromium 기반, macOS 15+·Windows
  - Claude Code 연결: MCP 서버. 설정 `{"mcpServers": {"aside": {"command": "aside", "args": ["mcp"]}}}` → `claude mcp add --scope user aside -- aside mcp`. CLI는 `aside "작업"`. 출처: https://docs.aside.com/help/developers.md (2026-09-24 확인)
  - 요금: Free 월 500 크레딧(Vault·메모리·CLI·MCP, 루틴 3개), Pro 1,500, Max 15,000. Claude Pro/Max 구독이나 API 키를 연결하면 크레딧을 쓰지 않음. 출처: https://daleseo.com/aside/ (공식 가격 페이지 https://aside.com/pricing 에서 재확인 필요)
  - 자격 증명: Vault에 암호화 저장, 모델에는 "로그인" 동작만 전달, 대상 URL 검사
  - 앱이 켜져 있어야 MCP가 동작하는지: 문서에 없음(확인 필요)
  - **앱을 설치해도 CLI(`aside` 명령)는 따로 설치해야 한다**(2026-09-24 확인: 앱은 `C:\Program Files\Aside`에 있었지만 `aside` 명령이 없었다). 가장 쉬운 방법은 Aside 앱의 개발자 설정 페이지에서 CLI 설치. 공식 PowerShell 설치 스크립트도 있다(서명 검증 포함). 설치 후 새 터미널을 열어야 PATH가 잡힌다
  - **연결 확인됨(2026-09-24, Windows, CLI 1.26.916.1741):** CLI 위치 `%LOCALAPPDATA%\Aside\CLI\current\aside.exe`. PATH가 반영되기 전인 창에서도 되도록 전체 경로로 등록: `claude mcp add --scope user aside -- "C:\Users\<사용자>\AppData\Local\Aside\CLI\current\aside.exe" mcp` → `claude mcp list`에서 `✔ Connected`. Aside 도구는 Claude를 **재시작해야** 세션에 나타난다
