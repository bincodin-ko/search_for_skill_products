---
name: idea-lab
description: 될 놈 실험실 — 아이디어 여러 개를 5단계 깔때기(Ideation → Incubating → Brainstorming → Filtering(FDT, 가짜 문 테스트) → 2일마다 리뷰)로 동시에 굴려서, 수요가 증명되고 해자가 있는 것만 남긴다. 신호 하베스트로 후보를 모으고, 경쟁사·가격·빈틈 조사를 근거로 채점하고, 메인이 핵심 근거를 직접 검증한 뒤 가짜 문 테스트로 넘긴다. 보드(lab/board.json)와 칸반 대시보드로 관리한다. "실험실", "될놈실험실", "아이디어 여러 개 걸러줘", "아이디어 더 찾아줘", "FDT", "페이크 도어", "아이디어 보드", "실험실 리뷰해줘" 같은 말이 나오면 사용. 아이디어 하나를 깊게 설계하는 건 idea-blueprint.
---

# idea-lab (될 놈 실험실)

위프 팀의 "될 놈 실험실 Process"(릴스 `Ddi6CRfTQBY` 11~14초 흐름도)를 1인용으로 옮긴 스킬이다. 조사는 서브에이전트가, **판정과 검증은 메인이**, 최종 확인은 사용자가 한다.

세부 규칙은 필요할 때만 읽는다:
- `references/commands.md` — `LAB` 명령 전체와 주의사항
- `references/harvest.md` — 1단계 발굴(신호 하베스트·증거 세 개·마켓 캐시·사전 필터)
- `references/research.md` — 3단계 조사·채점 기준표·예외 후보·피벗
- `references/fdt.md` — 4단계 표본 검증·정성 게이트·묶음·가짜 문 테스트
- `references/logins.md` — 로그인 출처(Aside) 규칙·세션 점검·`LAB gated`·사이트별 요령. **읽기만 한다**
- `templates/` — 조사원·하베스터 공통 지시문(`RESEARCH_PROMPT.md`, `HARVEST_PROMPT.md`)과 FDT 페이지(`fdt.html`). `LAB init`이 지시문을 `lab/batches/`로 복사한다

## 원칙
- 한 바퀴의 목표는 **프로토타입 우선순위 리스트**. 통과한 것만 `idea-blueprint`로 넘긴다
- **빨리 많이 버린다.** 애매하면 Drop하거나 대기시킨다
- **근거 없이 채점하지 않는다.** 조사 뒤에 채점하고, 추정이 섞이면 보고에 "추정"이라고 적는다
- **조사원 근거를 그대로 믿지 않는다.** 4단계로 올리기 전에 메인이 핵심 근거를 직접 연다(표본 검증). 실측상 "경쟁 제품이 없다"와 가격 단위가 가장 자주 틀린다
- **규칙이 의견보다 우선한다.** need·revenue ≤ 2면 Drop. 예외 후보를 살릴지는 사용자가 정한다
- 모든 이동은 `LAB move ... --reason "근거"`. 보드는 `LAB`으로만 고친다
- 사용자에게 시키는 일: 최초 설정(창업자 프로필·분석 도구 — 필요한 순간 한 번씩), FDT 트래픽, 로그인이 필요한 출처 열어 주기, 판정 확인. 사용자 이름으로 외부에 연락하는 일은 초안까지만
- **사용량을 아낀다.** 조사원·하베스터는 Sonnet, 동시 4명 이하, 하위 에이전트 금지(프롬프트에 직접 적는다), 결과는 한 줄씩 즉시 저장(`.jsonl`)

## 역할
| 역할 | 누가 | 맡는 일 |
|---|---|---|
| 하베스터 | 서브에이전트(Sonnet) | 1단계 신호 수집 |
| 리서처 | 서브에이전트(Sonnet) | 3단계 조사, 4단계 원문 보강 |
| 결정권자·검증자 | 메인 Claude | 채점 확정, 선검증·표본 검증, 판정 초안, 마켓 캐시, 로그인 출처(Aside, 읽기 전용 — `LAB gated`) |
| 확인자 | 사용자 | 예외·피벗 승인, 트래픽, 최종 판정 |

## 5단계 흐름

**1단계 Ideation** — 사용자가 준 아이디어는 P/S를 한 문장씩 채워 `LAB add`. 직접 발굴은 신호 하베스트로 한다: 후보마다 불편·지불·빈틈 증거 세 개, 하베스터별 통과율(`LAB stats`)과 고갈 지도(`LAB stats --tags`)로 비중을 정한다 → `references/harvest.md`

**선검증** — 조사원에게 보내기 전에 메인이 모든 후보를 기능 키워드로 1번씩 검색하고, 마켓 기반 후보는 Aside로 마켓 검색 목록도 뜬다. 이미 있는 건 바로 Drop(실측: 조사 통과 10개 중 7개가 기존 제품) → `references/harvest.md`

**2단계 Incubating** — "P-Code와 S-Code가 한 문장씩 명확한가?" 명확하면 `incubating` 후 바로 `brainstorming`(`LAB import`는 신호가 있으면 자동 통과). 두 번 불명확하면 Drop

**3단계 Brainstorming** — 리서처 조사 → `LAB apply`로 채점·자동 Drop → `LAB rank`로 순서 확인(평균 need·revenue·tenx·dist, 같으면 fit) → 올릴 것은 표본 검증 후 `move .. filtering`, `LAB rank --apply`로 우선순위 → `references/research.md`

**4단계 Filtering** — 표본 검증(`LAB verify`) → 정성 게이트 → 묶음(`LAB bundle`) → `LAB fdt-scaffold`로 랜딩페이지 → 배포·트래픽 → `LAB fdt`로 판정. 4·5단계 자리 수는 `max_parallel`(0 = 제한 없음, 이 보드는 0). 제한이 없으면 관문은 표본 검증뿐이고, FDT 순서는 `LAB rank`가 정한다 → `references/fdt.md`

**5단계 2일마다 리뷰** — `LAB due`로 오늘 볼 것. 가안(prelim)에서 출발해 FDT 결과로 확정:
- `easy`(5=따라 하기 어려움): 경쟁사가 금방 할 수 있나, 사용자 확보·운영 비용, 규제 / 데이터 확보, 최신 AI로 가능한가, 1인 기술력으로 되나
- `moat`: 네트워크 효과·쌓이는 데이터·독점 기술·규모의 경제·브랜드·전환 비용
- `scale`: 작게 시작해도 커질 길, 인접 타깃·기능
- 판정: 예 → `done --priority N` / 아니오 → `dropped` / 보완 → `review --verdict retry`(2일 뒤 재리뷰)

## 한 바퀴 마무리
1. DONE을 우선순위 표로(제목·P/S·FDT 가입률·easy/moat/scale·이유)
2. 1순위는 `idea-blueprint`로(조사 파일 함께)
3. `LAB exceptions`로 예외 후보·피벗안을 보여 주고 사용자가 고른 것만 살린다
4. `LAB stats`·`LAB stats --tags`로 다음 바퀴 하베스터 비중과 고갈 분야를 정한다
5. 바퀴마다 `lab/rounds/roundN.md`에 한 일·숫자·드러난 문제·보완을 남긴다

## 대시보드
- `LAB serve`를 백그라운드로 → `http://127.0.0.1:8765`(포트가 쓰이면 이미 떠 있는 것)
- 카드: 우선순위·평균 점수·FDT·`조사✓`·`검증✓/✗`·피벗 원본·묶음·예외 후보·태그. 검색·정렬·Drop 접기. 카드를 열면 조사 파일이 그대로 보인다
- CLI 변경은 5초 안에 반영되고, 오래된 화면의 저장은 막힌다. `lab.py`나 `dashboard.html`을 고치면 `serve`를 재시작한다

## 보고 형식
- 첫 줄: `LAB status` 그대로
- 이번에 판정한 것만 표로: 아이디어 · need · revenue · tenx · dist · fit · 판정 · **근거 한 줄**(검증한 사실). 추정이 섞이면 표 아래에 밝힌다
- 조사 상세는 "대시보드 카드 / `lab/ideas/<id>.md`"로 안내한다
- 마지막은 사용자가 할 일 1개
