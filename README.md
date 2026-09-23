# 스킬·제품 조사 노트

조사일: 2026-09-23 · 요청한 11개 항목을 순서대로 정리했습니다.

- 표기: **[확인]** 원문 페이지에서 직접 확인 · **[추정]** 제 판단 · **확인 불가** 막혀서 못 본 것
- 별 수·버전은 조사일 기준입니다.

## 스킬 설치 (Windows)

이 저장소에는 직접 만든 스킬 2개가 있습니다: `reel-analyzer`(릴스 자동 분석), `idea-blueprint`(아이디어 설계도).

**PC에 설치 (어느 폴더에서든 사용)** — 저장소 폴더에서 PowerShell:
```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\install-skills.ps1
```
- `%USERPROFILE%\.claude\skills\`에 복사됩니다. 터미널 `claude`와 데스크톱 앱의 **Local** 세션이 여기서 스킬을 읽습니다.
- 스킬을 고친 뒤 다시 실행하면 업데이트됩니다(이미 설치된 Python 환경은 유지).

**Claude 앱(채팅)에 올리기** — `idea-blueprint`만 해당:
```powershell
powershell -ExecutionPolicy Bypass -File .\install-skills.ps1 -Zip
```
`dist\idea-blueprint.zip`을 Claude 앱의 Customize → Skills → + → Create skill에서 업로드합니다. `reel-analyzer`는 PC의 크롬과 Python이 필요해서 채팅 앱에서는 동작하지 않습니다.

## 한눈에 보기

| # | 항목 | 한줄 결론 | 판정 | 바로 할 일 |
|---|---|---|---|---|
| 1 | Stanford CS146S | 코딩 에이전트로 개발하는 법을 10주에 정리한 무료 강의. 한국어판 있음 | **추천** | 한국어판 사이트에서 W4(Claude Code 자동화) 과제 열기 |
| 2 | json-render | AI가 허용된 컴포넌트 안에서만 JSON으로 화면을 만들게 하는 Vercel Labs 프레임워크. 스킬 34개 포함 | AI 제품에 **동적 UI가 필요할 때만** | `npx skills add vercel-labs/json-render --skill core` |
| 3 | bkit | 계획→설계→구현→검증 순서를 강제하는 Claude Code 플러그인(한국 팀). 기능이 많고 무거움 | 초·중급자에겐 도움, 숙련자에겐 과함 | 테스트용 프로젝트에 설치하고 `/control level 1`로 시험 |
| 4 | PowerShell로 아이폰↔갤럭시 사진 공유 | PowerShell은 폰에서 못 돌림. PC 변환기까지만 가능. 전송은 이미 AirDrop↔Quick Share로 해결됐고, **라이브↔모션 포토 변환**만 빈칸 | PowerShell로는 **불가**, 제품 기회는 있음 | 급하면 PC에서 [MotionPhoto2](https://github.com/PetrVys/MotionPhoto2) 사용 |
| 5 | awesome-mcp-servers | MCP 서버 약 4,200개 카탈로그. 대부분 개인 프로젝트 | 둘러보기용 | Context7 하나만 먼저 설치 |
| 6 | exploitarium | 개발사에 알리지 않고 공개한 제로데이 PoC 모음(45개, 라이선스 없음) | 데이터 활용 **하** / 방법론 참고 **중** | "PoC로 확인된 취약점만 보고"를 보안검사 제품의 핵심 기능으로 설계 |
| 7 | "worldflow AI" | WorldFlowAI가 복사해 둔 ECC(Everything Claude Code) 사본일 가능성 높음 | 사본은 쓰지 말 것 | Anthropic 공식 `claude-code-setup` 플러그인으로 추천 받기 |
| 8 | context-mode | 도구 출력 원문을 샌드박스에 가둬 컨텍스트 절약. "98%"는 최선의 경우 수치 | **필수 아님** | 세션이 자주 압축될 때만 한 프로젝트에서 시험 |
| 9 | 아이디어 구체화 도구 | 한 번에 다 해주는 도구는 없음. pm-skills + gstack + Lazyweb 조합이 최선 | 조합 추천 | gstack `/office-hours`로 아이디어 1개 돌려보기 |
| 10 | Aside (Windows 출시) | 에이전트 전용 브라우저(YC F25, 한국인 창업팀). 9월 14일 Windows 정식판 | **틈새 가치 있음**, 획기적은 아님 | Claude Pro/Max를 쓰고 있으면 건너뛰기 |
| 11 | 인스타 릴스 분석 | 이 클라우드 환경에선 인스타가 막혀 못 봄 → **PC에서 자동 분석하는 스킬**을 만들어 둠 | 스킬로 해결 | [릴스 자동 분석 사용법](#릴스-자동-분석-사용법-windows) 따라 하기 |

---

## 1. Stanford CS146S "The Modern Software Developer"

**한줄 요약:** Mihail Eric이 2025년 가을 스탠퍼드에서 가르친 강의입니다. 코딩 에이전트로 소프트웨어를 만드는 전 과정(프롬프팅 → MCP → 컨텍스트 관리 → Claude Code → 보안 → 코드 리뷰 → 운영)을 10주로 다룹니다. 슬라이드·읽을거리·과제가 무료입니다.

**핵심**
- 과제 레포 [확인]: `mihail911/modern-software-dev-assignments`, 별 약 4.8k, week1~8 폴더, Python 3.12 + Poetry
- 과제에서 만드는 것 [확인]
  - W2: Cursor로 FastAPI 메모 앱에 LLM 기능 추가
  - W3: 외부 API를 감싸는 MCP 서버 만들기
  - W4: Claude Code 자동화 2개 이상(슬래시 커맨드, CLAUDE.md, 서브에이전트, MCP)
  - W6: Semgrep 결과를 보고 AI로 취약점 3개 수정
  - W7: 직접 한 리뷰와 AI 리뷰 비교
- 게스트: Boris Cherny(Claude Code 제작자), Warp·Semgrep·Graphite·Vercel 관계자 등 [확인: 한국어판 syllabus]
- 한국어판 [확인]: `team-attention/stanford-cs146s-kr`, 원저자 허락을 받은 번역. 읽을거리와 주요 슬라이드 번역
- 2026 가을학기: 9월 22일 시작, 내용 약 85% 개편이라는 2차 출처가 있음 — 공식 사이트는 막혀서 **확인 불가**

**바로 할 일:** 한국어판에서 W3~W4 읽을거리를 읽고, 과제 레포의 W4를 내 프로젝트에 그대로 적용하기

**평가**
- 장점: 무료, 과제가 실무 그 자체, 도구를 만든 사람들이 게스트
- 단점: 게스트 강의 영상 대부분 비공개, 2025판은 특정 도구(Cursor·Warp·Graphite)에 묶여 빨리 낡음, 채점이 없어 혼자 끝까지 하기 어려움
- 추천 순서 [추정]: W4 → W3 → W6 → W7 → 나머지. W1은 훑고 넘어가도 됨

**출처:** [과제 레포](https://github.com/mihail911/modern-software-dev-assignments) · [한국어판](https://github.com/team-attention/stanford-cs146s-kr) · [공식 사이트](https://themodernsoftware.dev/) · [2026 학기 2차 출처](https://www.heyuan110.com/posts/ai/2026-09-11-cs146s-fall-2026-follow-along/)

---

## 2. json-render (vercel-labs/json-render)

**한줄 요약:** AI에게 코드를 쓰게 하지 않고, **개발자가 허용한 컴포넌트 목록 안에서만** JSON 스펙을 만들게 한 뒤 그걸 화면으로 그려주는 프레임워크입니다. React, React Native, Vue 등으로 스트리밍 렌더링합니다.

**핵심**
- 레포 [확인]: Apache-2.0, 별 약 18.1k, 최신 v0.21.0. 아직 0.x라 호환성 깨지는 변경이 있음
- **스킬 제공 [확인]:** 레포 `/skills` 폴더에 34개(core, react, react-native, shadcn, mcp 등)
- 구조: Catalog(허용 컴포넌트·액션을 Zod로 정의) → Registry(실제 컴포넌트 연결) → Spec(AI가 만든 JSON) → Renderer
- `catalog.prompt()`가 AI용 시스템 프롬프트를 자동으로 만들어줌
- `@json-render/mcp`로 Claude 대화창 안에 대시보드·폼 같은 UI를 띄울 수 있음

**바로 할 일**
```bash
npm i @json-render/core @json-render/react zod
npx skills add vercel-labs/json-render --skill core
```

**평가**
- 맞는 경우: 사용자 질문마다 대시보드·카드·폼 구성이 달라지는 AI 제품. 웹과 모바일에서 같은 스펙을 쓰고 싶을 때
- 안 맞는 경우: 화면이 고정된 앱. 도구 호출 1개에 컴포넌트 1개면 충분한 경우(이땐 Vercel AI SDK가 더 단순)
- 대안 [확인]: [Vercel AI SDK Generative UI](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces), [Google A2UI](https://github.com/google/A2UI), [CopilotKit](https://github.com/CopilotKit/CopilotKit), [Thesys C1](https://docs.thesys.dev/guides/what-is-thesys-c1)(유료)

**출처:** [레포](https://github.com/vercel-labs/json-render) · [skills 폴더](https://github.com/vercel-labs/json-render/tree/main/skills) · [InfoQ 기사](https://www.infoq.com/news/2026/03/vercel-json-render/)

---

## 3. bkit (Vibecoding Kit)

**한줄 요약:** POPUP STUDIO가 만든 Claude Code 플러그인입니다. 기능 하나를 계획→설계→구현→검증→개선 순서로 강제로 진행시키고, 구현이 설계 문서와 얼마나 맞는지 점수(matchRate)를 매겨 90% 미만이면 자동으로 고칩니다.

**핵심**
- 레포 [확인]: `popup-studio-ai/bkit-claude-code`(현재 `ww-w-ai/bkit-claude-code`로 연결), 별 약 600, Apache-2.0, 최신 v2.1.39(2026-09-20). 업데이트가 매우 잦음
- 규모(README 자체 수치): 스킬 44개, 에이전트 34개, 품질 게이트 11개, 훅 21종
- 핵심 명령: `/pdca`(기능 하나 전 과정), `/sprint`(여러 기능 묶음), `/control level 0~4`(자율도, 기본 L2)
- 한국어로 "로그인 기능 만들어줘"라고 해도 해당 명령이 실행됨
- Gemini CLI용 `bkit-gemini`, Codex용 `bkit-codex`도 있음 [확인]

**바로 할 일**
```
/plugin marketplace add popup-studio-ai/bkit-claude-code
/plugin install bkit
```
설치 후 테스트용 프로젝트에서 `/control level 1`(계획 뒤에 멈춤)로 시험

**평가**
- 장점: 혼자 개발할 때 빠지기 쉬운 문서화와 QA를 자동으로 챙겨줌
- 위험 [추정]: 스킬 44개와 훅 때문에 컨텍스트·비용 부담이 큼. matchRate는 AI가 AI를 채점하는 구조. 릴리스 노트에 "QA가 아무것도 측정 안 하고 성공 보고" 버그 수정 이력이 있어 아직 안정화 중
- 추천 대상: 방법론 없이 바이브코딩하다 품질 문제를 겪은 사람. 이미 CLAUDE.md·서브에이전트를 직접 다루는 사람은 필요한 스킬만 가져다 쓰는 편이 나음

**출처:** [레포](https://github.com/popup-studio-ai/bkit-claude-code) · [릴리스](https://github.com/popup-studio-ai/bkit-claude-code/releases) · [bkit-gemini](https://github.com/popup-studio-ai/bkit-gemini) · [bkit-codex](https://github.com/popup-studio-ai/bkit-codex)

---

## 4. PowerShell로 아이폰↔갤럭시 사진 공유 (라이브·모션 포토 포함)

**한줄 요약:** "powershell:os"는 운영체제가 아니라 [PowerShell/PowerShell](https://github.com/PowerShell/PowerShell)(Windows·macOS·Linux용) 또는 도커 이미지 `mcr.microsoft.com/powershell:<태그>`로 보입니다. **iOS·Android는 공식 지원이 없어서** 폰끼리 자동으로 되게 만들 수는 없습니다. PC를 변환기로 두는 방식까지만 됩니다.

**두 포맷의 차이 [확인]**

| | 아이폰 라이브 포토 | 갤럭시 모션 포토 |
|---|---|---|
| 구조 | 파일 2개(사진 HEIC + 영상 MOV) | 파일 1개(JPG 끝에 MP4를 붙임) |
| 연결 방식 | 두 파일에 같은 고유 ID | 사진 메타데이터(XMP)에 영상 위치 기록 |
| 상대 폰으로 보내면 | 갤럭시는 대개 정지 사진만 받음 | 아이폰은 정지 사진으로만 보여줌 |

**2026년 9월 현재 상황 [확인]**
- 갤럭시 S26부터(한국 먼저, 3월) AirDrop과 Quick Share가 서로 됨. 5월 One UI 8.5로 S24·S25·폴드/플립 6·7까지 확대
- 5월부터 모든 안드로이드에서 QR 코드로 아이폰에 보내기 가능
- **하지만 전부 파일을 그대로 옮길 뿐, 라이브↔모션 변환은 안 해줌**
- Google 포토·Immich·LocalSend도 상대 OS 기기로 내려받으면 움직임이 사라짐

**지금 쓸 수 있는 변환 도구 [확인]**
- 아이폰→갤럭시: [MotionPhoto2](https://github.com/PetrVys/MotionPhoto2) — 원래 PowerShell 스크립트로 시작한 도구. Windows에서 동작
- 갤럭시→아이폰: [Motion2Live](https://github.com/Igloo302/MotionPhotoConverter) — 아이폰 앱에서 직접 변환
- Mac 전용: [makelive](https://github.com/RhetTbull/makelive)

**할 수 없는 것**
- 폰에서 PowerShell 실행
- AirDrop/Quick Share 전송 중간에 끼어들어 변환
- Windows만으로 아이폰 사진 보관함에 라이브 포토 등록(Mac 또는 iOS 앱 필요)

**바로 할 일:** 갤럭시 S24 이상이면 AirDrop으로 보내고, 움직임이 필요하면 받는 쪽에서 위 변환 도구 사용

**제품 기회 [추정]:** "받는 기기의 OS에 맞춰 포맷을 바꿔 전달하는 공유앨범"은 아직 아무도 제대로 안 함. 만들려면 PowerShell이 아니라 앱(iOS PhotoKit + Android MediaStore)으로 만들어야 함

**출처:** [PowerShell 릴리스](https://github.com/PowerShell/PowerShell/releases) · [Android 지원 요청 거절 이슈](https://github.com/PowerShell/PowerShell/issues/25050) · [모션 포토 포맷 사양](https://developer.android.com/media/platform/motion-photo-format) · [삼성 AirDrop 지원](https://news.samsung.com/us/samsung-airdrop-quick-share-galaxy-s26-series/) · [MacRumors: AirDrop 지원 기종](https://www.macrumors.com/2026/05/13/every-android-phone-getting-airdrop-support/) · [Immich 토론](https://github.com/immich-app/immich/discussions/25746)

---

## 5. awesome-mcp-servers

**한줄 요약:** MCP 서버를 모아둔 가장 큰 목록입니다([punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers), 별 약 95k). 여기서 바로 설치하기보다 **무엇이 있는지 둘러보는 카탈로그**로 쓰고, 실제 설치는 회사가 직접 운영하는 공식 서버 위주로 하는 게 안전합니다.

**핵심 [확인]**
- 항목 약 4,200개, 그중 🎖️(공식) 약 390개. 카테고리 55개 안팎. 한국어 README 있음
- 아이콘: 🎖️ 공식 · ☁️ 원격 API · 🏠 내 PC에서 실행 · 🐍📇🏎️ 개발 언어
- 다른 목록: `appcypher` 목록은 2026-08-01 보관 처리(갱신 중단). 공식 [MCP Registry](https://registry.modelcontextprotocol.io/)도 있음
- 주의: 목록의 Postgres·Puppeteer 항목은 이미 보관된(관리 안 되는) 저장소를 가리킴

**1인 개발자 추천 서버 (공식·호스팅 위주)**

| 서버 | 용도 | 설치 |
|---|---|---|
| Context7 | 최신 라이브러리 문서 | `claude mcp add --transport http context7 https://mcp.context7.com/mcp` |
| Sentry | 에러 분석 | `claude mcp add --transport http sentry https://mcp.sentry.dev/mcp` |
| Figma | 디자인 → 코드 | `claude mcp add --transport http figma https://mcp.figma.com/mcp` |
| Notion | 문서 | `claude mcp add --transport http notion https://mcp.notion.com/mcp` |
| Supabase | DB (운영 DB엔 연결 금지, 읽기 전용 권장) | 원격 주소 `https://mcp.supabase.com/mcp` |

- GitHub·Vercel·Stripe·Supabase는 **CLI(`gh` 등)가 컨텍스트를 덜 먹음** — 공식 문서도 권장

**보안 주의 [확인]**
- 외부 글을 읽는 서버는 숨겨진 지시(프롬프트 인젝션)에 당할 수 있음. 실제로 GitHub MCP로 비공개 저장소를 빼내는 공격이 시연됨
- 내 PC에서 도는 서버는 내 권한으로 아무 코드나 실행 가능
- 안 쓰는 서버는 `/mcp`에서 끄고, `/context`로 공간 차지 확인

**바로 할 일:** Context7 하나만 설치하고 1주일 써보기

**출처:** [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) · [Claude Code MCP 문서](https://code.claude.com/docs/en/mcp) · [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) · [Invariant Labs 공격 사례](https://invariantlabs.ai/blog/mcp-github-vulnerability)

---

## 6. exploitarium

**한줄 요약:** "bikini"라는 익명 연구자가 2026년 6월 GitHub에 올린 **공개 PoC(취약점 증명 코드) 모음**입니다([bikini/exploitarium](https://github.com/bikini/exploitarium)). 개발사에 먼저 알리지 않고 공개해서 논란이 됐습니다.

**정체 [확인]**
- 폴더 약 45개, 별 5.1k, 포크 1.3k. **라이선스 명시 없음**
- 대상: libssh2, Gitea, FFmpeg, RustDesk, OpenVPN, ImageMagick, QEMU, PHP, 7-Zip 등 오픈소스·네이티브 소프트웨어
- 방법: 작성자가 "퍼징(자동으로 이상한 입력을 넣어 버그를 찾는 기법)은 전부 GPT-5.3으로 자동화, PoC는 직접 작성"이라고 밝힘
- 보안 업계 보도에 따르면 libssh2 인증 전 힙 쓰기, Gitea 기본 Docker 설정 인증 우회는 실제 공격이 관측됨
- 방어 쪽 파생물도 나옴: [Exploitarium-Detections](https://github.com/Ethan-Andrews/Exploitarium-Detections)(탐지 규칙)

**"이걸로 코딩 보안검사 제품을 획기적으로 만들 수 있나?" — 냉정한 분석 [추정]**
- **데이터로 쓰기: 하**
  - 45개는 학습·규칙용으로 너무 적음
  - 라이선스가 없어서 코드를 제품에 넣거나 재배포할 수 없음
  - 대부분 C/C++ 메모리 버그라서, 바이브코딩 웹앱(Next.js·Supabase·Firebase)을 검사하는 제품과는 대상이 다름
  - 제보 없이 공개된 익스플로잇을 제품 근거로 쓰면 평판 위험
- **방법론 참고: 중**
  - 진짜 신호는 "AI 퍼징 + PoC로 실제 공격 가능성 확인"이 1명으로도 이만큼 된다는 것
  - 보안검사 제품의 최대 불만은 **오탐(가짜 경고)** 이므로, "샌드박스에서 PoC를 만들어 실제로 터지는 것만 보고"하는 기능이 차별점이 됨
- 할 수 있는 합법적 활용: 내 스캐너의 **내부 평가셋**(해당 버전 코드를 잡아내는지 테스트)으로만 쓰고, 코드는 재배포하지 않기
- **경쟁이 이미 셈**
  - Anthropic Claude Code Security(2026-02 출시), OpenAI Aardvark/Codex Security, Google CodeMender가 "찾기 + 공격 가능성 확인 + 수정 제안"을 이미 함
  - 1인 개발자가 이기려면 틈새가 필요

**바로 할 일:** 틈새 1개를 정해 MVP 범위로 좁히기. 후보:
- 바이브코딩 앱 전용: Supabase RLS 누락, 키 노출, Firebase 규칙, Next.js 서버 액션 인증 누락을 **PoC로 확인해서** 보고
- 한국 규제용 리포트: 개인정보보호법·ISMS-P 점검표 형식으로 결과 출력

**출처:** [bikini/exploitarium](https://github.com/bikini/exploitarium) · [Field Effect 분석](https://fieldeffect.com/blog/exploitarium-repository-publishes-poc-exploits) · [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/researcher-exploitarium-exploits/) · [IT-Connect](https://www.it-connect.tech/exploitarium-researcher-exposes-zero-day-flaws-in-15-open-source-projects/) · [Checkmarx: CodeMender·Aardvark](https://checkmarx.com/blog/codemender-aardvark-and-the-rise-of-agentic-appsec-what-developers-need-to-know/) · [The Register: Claude Code Security](https://www.theregister.com/security/2026/02/23/infosec-community-panics-over-anthropic-claude-code-security/4898318)

---

## 7. "클로드 설정 자동으로 해주는 worldflow AI"

**한줄 요약:** 가장 유력한 후보는 [`WorldFlowAI/everything-claude-code`](https://github.com/WorldFlowAI/everything-claude-code)입니다. 유명한 **ECC(Everything Claude Code, [affaan-m/ECC](https://github.com/affaan-m/ECC))를 1월에 복사해 둔 사본**이라 1월 이후 갱신이 없습니다. 쓸 거라면 원본이나 공식 플러그인을 쓰세요. (신뢰도 중간 — 사용자가 본 게 정확히 이건지는 확인 불가)

**핵심 [확인]**
- WorldFlow AI는 LLM 인프라 회사이고, 이 저장소는 사내용 가이드 1개를 추가한 사본
- 원본 ECC: 별 약 266k, v2.2.2(2026-08-31), 에이전트 68개·스킬 292개·명령 94개. 원본 README가 "공식 채널에서만 설치하라"고 명시
- ECC 설치: `npx ecc-universal@2.2.2 setup`(설치 전 점검·확인 절차, `uninstall --dry-run` 지원)

**다른 후보**
1. **Anthropic 공식 `claude-code-setup` 플러그인 (가장 안전)** — 코드를 분석해 MCP·스킬·훅·서브에이전트를 추천만 하고 **파일은 안 건드림**
2. Ruflo(구 claude-flow) — 훅 27개, 도구 약 210개를 자동 등록. 매우 무겁고, 일부 문서가 권한 확인을 끄는 옵션(`--dangerously-skip-permissions`)을 언급하므로 주의
3. [claude-code-templates](https://github.com/davila7/claude-code-templates) — 필요한 것만 골라 설치

**바로 할 일**
```
/plugin install claude-code-setup@claude-plugins-official
```
그다음 "이 프로젝트에 맞는 자동화 추천해줘"라고 요청 → 추천 중 필요한 것만 추가

**평가:** 올인원 패키지는 "뭘 설치했는지 모르는" 상태를 만들고 컨텍스트를 많이 먹습니다. `/init` + 공식 플러그인 추천 → 필요한 것만 수동 추가가 1인 개발자에게 맞습니다.

**출처:** [WorldFlowAI 사본](https://github.com/WorldFlowAI/everything-claude-code) · [커밋 기록](https://github.com/WorldFlowAI/everything-claude-code/commits/main) · [ECC 원본](https://github.com/affaan-m/ECC) · [claude-code-setup README](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/claude-code-setup/README.md) · [Ruflo](https://github.com/ruvnet/claude-flow)

---

## 8. context-mode

**한줄 요약:** [`mksglu/context-mode`](https://github.com/mksglu/context-mode)는 명령 실행 결과·파일 원문을 샌드박스에 가둬두고, Claude에게는 출력 결과나 검색 결과만 넘겨서 컨텍스트를 아끼는 플러그인입니다. 별 약 24k.

**핵심 [확인]**
- 방식: 훅이 Bash·Read·WebFetch 호출을 가로채 샌드박스 도구로 돌림. 원문은 SQLite 검색 인덱스에 넣고 필요한 부분만 검색
- 압축 직전 작업 상태를 2KB 스냅샷으로 저장했다가 복원
- 절감 수치: 대표 수치 98%, 벤치마크 21개 전체 평균 96%, 문서 검색은 82%
- **바이트만 쟀고 답변 품질·작업 성공률은 안 쟀다고 문서에 명시**
- 라이선스 ELv2: 개인 사용은 가능, 이걸로 호스팅 서비스 만드는 건 제한

**바로 할 일:** 세션이 자주 압축되는 프로젝트가 있을 때만
```
/plugin marketplace add mksglu/context-mode
/plugin install context-mode@context-mode
```
설치 후 `ctx stats`와 `/context`로 효과 확인

**평가:** 대부분은 **필수 아님**. Claude Code는 이미 MCP 도구를 필요할 때만 불러오고, 긴 출력은 25k 토큰에서 잘라 파일로 뺍니다. 서브에이전트 활용, `/clear` 습관, 안 쓰는 MCP 끄기로 먼저 해결해 보세요. 훅이 기본 동작을 바꾸므로 원문 세부를 놓치거나 다른 플러그인과 충돌할 수 있습니다 [추정].

**출처:** [context-mode](https://github.com/mksglu/context-mode) · [BENCHMARK.md](https://github.com/mksglu/context-mode/blob/main/BENCHMARK.md) · [Claude Code 비용·컨텍스트 문서](https://code.claude.com/docs/en/costs)

---

## 9. 아이디어 구체화 스킬·제품

**한줄 요약:** 디자인·기능·초기 고객·경쟁사·유저 플로우를 **한 문서로 다 뽑아주는 도구는 없습니다.** 무료 조합으로 대부분 채울 수 있습니다: **pm-skills**(전체 흐름) + **gstack**(아이디어 압박 질문, 경쟁사 디자인 분석) + **Lazyweb**(실제 앱 화면·플로우 레퍼런스).

**단계별 추천 도구**

| 단계 | 도구 | 비용 |
|---|---|---|
| 1. 문제·고객 정의 | gstack `/office-hours`, pm-skills `/discover`·`/interview` | 무료 |
| 2. 경쟁사·롤모델 조사 | pm-skills `/competitive-analysis`, BMAD Analyst, Similarweb 무료 조회 | 무료 |
| 3. UI/UX·플로우 레퍼런스 | Lazyweb `/lazyweb-search-flows`, gstack `/design-consultation`(경쟁사 3~5곳 캡처 → DESIGN.md), Mobbin MCP(유료) | 무료 / Mobbin 약 $10/월 |
| 4. MVP 범위·유저 플로우 | pm-skills customer-journey-map, gstack `/plan-ceo-review`(범위 축소 모드), BMAD `bmad-ux` | 무료 |
| 5. 초기 고객 확보 | pm-skills `/plan-launch`, 디스콰이엇, Product Hunt, F5Bot | 무료 |
| 6. PRD·시안 | `doc-coauthoring` → `design-router`(이미 설치된 스킬) | 무료 |

- [phuryn/pm-skills](https://github.com/phuryn/pm-skills) — 별 26.5k, MIT
- [garrytan/gstack](https://github.com/garrytan/gstack) — 별 133.9k, MIT
- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) — 별 53.4k, 한국어 문서 있음
- [Lazyweb 스킬](https://github.com/aboul3ata/lazyweb-skill) — 무료 범위는 확인 필요
- [Anthropic knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) — 공식, `/competitive-brief`·`/write-spec`

**빈칸 [추정]**
- 경쟁사 온보딩을 "몇 단계 만에 첫 가치에 도달하나, 결제벽은 어디인가"로 분해해주는 도구가 없음
- 네이버·카카오 오픈채팅·디스콰이엇 같은 **국내 채널용 첫 고객 계획**이 없음
- → 둘 다 채우는 커스텀 스킬 `idea-blueprint`를 만들 만함(목차: 판정 → 문제·고객 → 수요 신호 → 경쟁사 표 → 롤모델 UX 해부 → 디자인 방향 → MVP 범위 → 유저 플로우 → 첫 100명 계획 → 성공·중단 기준)

**바로 할 일:** gstack 설치 후 아이디어 1개로 `/office-hours` 돌려보기 (약 20분)

**직접 만든 스킬: [`idea-blueprint`](.claude/skills/idea-blueprint/SKILL.md)** — 위 빈칸을 채우는 용도
- 순서: 문제 정의 → **조기 중단 검토(필요성·수익성 점수, 필요 유료 고객 수 계산 → 가망 없으면 바로 접음)** → 수요 → 경쟁사 → 롤모델 UX 해부 → 디자인 → 첫 출시 범위(3주, 기능 넓게) → 화면 단위 유저 플로우 → 초반 입지·인지도 전략 → 출시 후 중단 기준
- 사용: 이 저장소에서 Claude를 실행하고 `이 아이디어 블루프린트 만들어줘: <아이디어 한 줄>`
- 결과: `docs/blueprint/<이름>.md`

**출처:** 위 링크 + [Lenny: 첫 1,000명 확보 전략](https://www.lennysnewsletter.com/p/how-the-biggest-consumer-apps-got) · [Mobbin MCP](https://mobbin.com/mcp) · [디스콰이엇](https://disquiet.io/)

---

## 10. Aside (Windows 출시)

**한줄 요약:** [aside.com](https://aside.com/)의 **AI 에이전트 브라우저**입니다. 크롬 같은 브라우저 자체에 에이전트가 들어 있어서, 로그인된 사이트에서 사람처럼 클릭하며 일을 처리합니다. YC F25 출신 한국인 창업팀이 6월 23일 macOS로 출시했고, **9월 14일 Windows 정식판**을 냈습니다.

**핵심**
- 기능: 장시간 자율 작업(Ultrabrowse), 예약 작업(Routines), AI가 비밀번호를 보지 않는 로그인, 기기 내 메모리, MCP 지원
- 모델: GPT-5.5 등 여러 회사 모델 사용 [확인: 자체 벤치마크 저장소]
- 벤치마크: Online-Mind2Web 99% — **회사 자체 보고, 제3자 재현 없음**
- 요금: 무료(월 500 크레딧), Pro $20, Max $200 — 2차 출처만 확인
- 주의: "Claude 구독 연결"은 Anthropic 정책과 충돌 가능. 2026-02부터 개인 구독을 제3자 제품에서 쓰는 걸 금지 → 사실상 API 키(종량 과금) 필요 [추정]

**Claude Desktop과 비교**

| 기능 | Aside | Claude Desktop |
|---|---|---|
| 로그인된 웹 작업 | 핵심 기능 | Claude in Chrome(8월 모든 유료 플랜 정식), Cowork |
| 브라우저 밖 앱 조작 | 확인 불가(브라우저 한정으로 보임) | computer use(Mac·Windows, 베타) |
| 파일 작업 | 제한적 | Cowork에서 폴더 읽기·쓰기 |
| 예약 작업 | Routines(무료는 3개) | Cowork 예약 작업(PC 꺼져도 동작) |
| 모델 선택 | 여러 회사 | Claude만 |
| 비용 | 크레딧 + 모델 비용 별도 | 구독에 포함 |

**냉정한 판정: 틈새 가치 있음, 획기적은 아님**
- Claude가 못 하는 건 두 가지뿐: ① GPT 등 다른 모델로 도는 브라우저 에이전트 ② 에이전트 전용으로 설계된 브라우저(비밀번호 격리)
- ChatGPT Atlas, Comet, Dia, Claude in Chrome과 경쟁이 치열하고, 출시 3개월이라 초기 버그 보고가 있음
- 쓸 만한 사람: 하루 대부분을 웹 SaaS 반복 클릭으로 보내는 사람, 여러 모델을 병용하려는 사람
- 안 써도 되는 사람: **이미 Claude Pro/Max로 Cowork·Claude in Chrome을 쓰는 사람** — 기능 중복에 비용만 추가

**바로 할 일:** Claude Pro/Max 사용 중이면 건너뛰기. 경쟁 동향만 보려면 무료 플랜 설치

**출처:** [PiunikaWeb: Windows 출시](https://piunikaweb.com/2026/09/14/aside-ai-browser-windows-release/) · [Y Combinator: Aside](https://www.ycombinator.com/companies/aside) · [자체 벤치마크](https://github.com/at-inc/aside-benchmarks) · [eesel: 요금](https://www.eesel.ai/blog/aside-ai-browser-pricing) · [Claude in Chrome 정식 출시](https://gigazine.net/gsc_news/en/20260827-claude-chrome-available/) · [Cowork computer use](https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork) · [The Register: 제3자 구독 사용 금지](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)

---

## 11. 인스타 릴스: AI로 돈 되는 아이디어 찾는 법

**확보 결과:** 이 클라우드 세션은 네트워크 정책으로 인스타그램이 막혀 있고, 미러·아카이브 사이트 약 30곳도 모두 실패했습니다. **릴스 내용은 추측으로 채우지 않았습니다.** 대신 PC에서 자동으로 분석하는 스킬을 만들었습니다(아래 사용법).

### 릴스 자동 분석 사용법 (Windows)

처음 한 번만 (약 5분):
1. PowerShell 열고 Claude Code 설치(이미 있으면 건너뛰기)
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
2. 이 저장소 받고 스킬 설치
   ```powershell
   git clone https://github.com/bincodin-ko/search_for_skill_products
   cd search_for_skill_products
   powershell -ExecutionPolicy Bypass -File .\install-skills.ps1
   ```
   git이 없으면 GitHub에서 ZIP으로 받아 압축 풀고 그 폴더에서 PowerShell 열기
3. 크롬 연동으로 실행 (아무 폴더에서나 가능)
   ```powershell
   claude --chrome
   ```
   처음 뜨는 안내에서 Enter → `/chrome` 입력 → "Enabled by default" 선택
4. 크롬에서 인스타그램 로그인 상태 확인

그다음부터는 이것만:
```
릴스 분석해 https://www.instagram.com/reel/Ddi6CRfTQBY/
```

- 첫 실행: Python·받아쓰기 엔진·한국어 음성 모델(약 1.6GB)을 설치하느라 약 10분. 권한 확인 창이 몇 번 뜨면 허용
- 이후: 릴스 1개에 약 1~2분
- 결과: 실행한 폴더의 `reels/<릴스ID>/analysis.md`
- 동작 원리와 파일 구성: [`.claude/skills/reel-analyzer/SKILL.md`](.claude/skills/reel-analyzer/SKILL.md)

### 릴스와 별개로: 검증된 방법 (2025~2026)
1. **불만 문장 모으기 → AI로 분류·점수화.** "이런 툴 없나요", "엑셀로 일일이" 같은 글을 원문 링크와 함께 모으고, 같은 불만이 **여러 커뮤니티에서 반복**되는지 봄. Reddit은 2025년 11월부터 API 사용을 승인제로 바꿨으므로 대량 크롤링 대신 소량을 꼼꼼히
2. **경쟁 제품의 1~3점 리뷰 분석.** G2·앱스토어의 낮은 별점 리뷰에 빠진 기능이 구체적으로 적혀 있음
3. **트렌드 확인.** Google Trends, Exploding Topics, 국내는 **네이버 데이터랩**
4. **국내 수요처.** 크몽·숨고 요청서(이미 돈을 내는 수요), 네이버 카페·지식iN 반복 질문, 국내 경쟁 앱 낮은 별점
5. **만들기 전에 팔아보기.** Mom Test 인터뷰(의견 말고 과거 행동을 묻기), 랜딩 페이지 + 가격표로 클릭 반응 보기(Buffer 사례: 7주 만에 첫 유료 고객)

**냉정하게:** "AI야 아이디어 20개 뽑아줘"는 거의 가치가 없습니다. **원문 근거, 돈을 낸 흔적, 고객에게 닿을 경로** 세 가지가 없는 아이디어는 버리세요.

**바로 쓸 수 있는 프롬프트 (Claude에 그대로 붙여넣기)**
> 웹 검색으로 최근 12개월 한국어 공개 글(지식iN, 공개 카페글, 커뮤니티)에서 "[업무] 너무 불편", "자동화 방법 없나요", "엑셀로 일일이"를 찾아 20건 모아줘. 각 건마다 ①원문 인용 ②URL ③지금 쓰는 대체 수단 ④돈이나 시간 손실 언급을 표로 정리해. 원문에 없는 내용은 "없음"으로 적고 추측하지 마.

> 위 표를 '문제' 단위로 묶어줘. 묶음마다 언급 수, 서로 다른 출처 수, 지불 흔적(외주·유료 툴·사람 고용), 긴급도(1~5)를 매기고 근거 행 번호를 달아. 상위 3개만 남기고 탈락 이유도 한 줄씩.

- 이미 설치된 `solo-biz-idea-finder` 스킬이 이 흐름을 단계별로 진행해줌

**출처:** [The Rundown: AI Pain Radar](https://app.therundown.ai/guides/mine-reddit-complaints-into-business-ideas-with-an-ai-pain-radar) · [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) · [HN: G2 부정 리뷰 분석](https://news.ycombinator.com/item?id=42677886) · [네이버 데이터랩 가이드](https://www.ascentkorea.com/naver-datalab-guide/) · [Buffer 사례](https://buffer.com/resources/idea-to-paying-customers-in-7-weeks-how-we-did-it/) · [The Mom Test 요약](https://mtlynch.io/book-reports/the-mom-test/) · [yt-dlp 인스타 로그인 요구 이슈](https://github.com/yt-dlp/yt-dlp/issues/11166) · [Claude Code 크롬 연동 문서](https://code.claude.com/docs/en/chrome)
