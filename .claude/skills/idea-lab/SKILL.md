---
name: idea-lab
description: 될 놈 실험실 — 아이디어 여러 개를 5단계 깔때기(Ideation → Incubating → Brainstorming → Filtering(FDT, 가짜 문 테스트) → 2일마다 리뷰)로 동시에 굴려서, 수요가 증명되고 해자가 있는 것만 남긴다. 보드(lab/board.json)와 칸반 대시보드로 관리한다. "실험실", "될놈실험실", "아이디어 여러 개 걸러줘", "FDT", "페이크 도어", "아이디어 보드", "실험실 리뷰해줘" 같은 말이 나오면 사용. 아이디어 하나를 깊게 설계하는 건 idea-blueprint, 아이템 발굴은 solo-biz-idea-finder.
---

# idea-lab (될 놈 실험실)

위프 팀의 "될 놈 실험실 Process"(릴스 `Ddi6CRfTQBY` 11~14초 흐름도)를 1인용으로 옮긴 스킬이다. 팀원 3명이 맡던 역할은 Claude 서브에이전트가 나눠 맡고, 사용자는 **판정만 확인**한다.

## 원칙

- 한 바퀴의 목표는 **프로토타입 우선순위 리스트**다. 통과한 것만 `idea-blueprint`로 넘긴다.
- **빨리 많이 버린다.** 애매하면 붙잡지 말고 Drop하거나 대기시킨다.
- 동시에 실험하는 아이디어(4·5단계)는 최대 `max_parallel`개(기본 10개)다.
- 판정에는 근거를 남긴다. 모든 이동은 `lab.py move ... --reason`으로 기록한다.
- 사용자에게 시키는 일은 두 가지뿐이다: FDT 페이지에 방문자를 보내는 일(트래픽), 최종 판정 확인.

## 파일과 명령

- 보드: 현재 폴더의 `lab/board.json` (없으면 `init`)
- 아이디어별 메모: `lab/ideas/<id>.md` (근거 링크, 조사 결과)
- FDT 페이지: `lab/fdt/<id>/index.html`
- `LAB`: `python "<이 스킬 폴더>/scripts/lab.py"` — 표준 라이브러리만 쓰므로 설치할 것 없음. Windows는 `py -3`
  - `LAB init` / `LAB add --title .. --p .. --s ..` / `LAB list` / `LAB show <id>`
  - `LAB move <id> <stage> --verdict go|drop|hold|retry --reason ".." [--priority N]`
  - `LAB score <id> need=4 revenue=3 easy=2 moat=3 scale=4`
  - `LAB fdt <id> --visits 320 --clicks 40 --signups 19 [--paid 2] [--url ..]`
  - `LAB due` (오늘 리뷰할 것) / `LAB serve` (대시보드 열기)
- stage 값: `ideation` `incubating` `brainstorming` `filtering` `review` `done` `dropped`

## 역할 (서브에이전트)

| 역할 | 원래 팀 | 맡는 단계 |
|---|---|---|
| 리서처 | Product Team | 4단계 정성 검증(유사 서비스, 커뮤니티, 리뷰) |
| 사업 검토자 | Pablo | 3단계 수익성, 5단계 해자·확장성 |
| 기술 검토자 | Ed + Tech | 5단계 기술 난이도, AI로 가능한가 |
| 결정권자 | Sora | 각 판정 마름모에서 최종 결정 초안 |

아이디어가 여러 개면 리서처·검토자를 **아이디어별로 병렬** 실행한다. 결정권자는 결과를 모아 판정 초안을 만들고, 사용자는 표로 한 번에 확인한다.

## 1단계: Ideation — P-Code × S-Code 발산

- **P-Code**: 누가, 어떤 상황에서, 어떤 문제를 겪는가
- **S-Code**: 그 문제에 대한 해결책과 수익 모델(BM)
- 사용자가 아이디어를 주면 그대로 `add`. 후보가 부족하면 `solo-biz-idea-finder`로 발굴하거나, P-Code 10개 × S-Code 방식(구독, 건당, 마켓플레이스, 대행) 조합으로 늘린다
- 목표: 한 바퀴에 20~50개

## 2단계: Incubating — P-S 명확성 판정

각 아이디어에 대해 결정권자가 묻는다: **"P-Code와 S-Code가 한 문장씩 명확한가?"**
- 명확함 → `move <id> incubating` 후 바로 `brainstorming`
- 불명확 → P/S를 다시 써서 1단계로 되돌린다(`--verdict retry`). 두 번 불명확하면 Drop

## 3단계: Brainstorming — 필터 기준 채점과 우선순위

아이디어당 약 20분 분량으로 사업 검토자가 채점한다(`LAB score`, 1~5점).
- `need` 필요성: 없으면 실제로 손해를 보나, 대체재로 해결되지 않나 (idea-blueprint 2단계 A와 같은 기준)
- `revenue` 수익성: 비슷한 제품이 돈을 받나, 목표 월수익(기본 300만 원)에 필요한 유료 고객 수를 1년 안에 모을 수 있나
- `tenx` 10배 요소: 10배 좋은 경험 / 10배 빠름 / 10배 싸다 / AI로 이제 막 가능해졌다 중 하나 이상
- **자동 Drop:** `need` ≤ 2 또는 `revenue` ≤ 2
- 남은 것 중 평균 점수로 우선순위를 매기고, 빈 병렬 자리만큼 `move <id> filtering --priority N`. 나머지는 3단계에 대기

## 4단계: Filtering — 시장에 실제 니즈가 있는가

**정성 검증 (리서처, 자동)**
- 유사 서비스 3개 이상과 가격, 커뮤니티 글·리뷰에서 불편 원문 3개 이상 → `lab/ideas/<id>.md`에 링크와 함께 기록

**정량 검증: FDT (가짜 문 테스트)**
1. `lab/fdt/<id>/index.html`에 한 파일 랜딩페이지를 만든다. `design-router`를 거쳐 만든다
   - 헤드라인(P-Code의 문제를 한 문장으로), 문제 3개, 해결 방식, **가격표(실제 가격을 적는다)**, 맨 아래 CTA "출시 알림 받기"
   - 폼은 무료 폼 서비스(Tally 등)를 임베드하거나 링크한다. 제출 후 "아직 준비 중이며 출시 때 가장 먼저 알려드립니다"를 보여준다(정직하게)
   - 방문 수 측정: 무료 분석 도구(Plausible, Umami, GA4 등) 스니펫 자리를 남기고 사용자에게 한 번만 선택받는다
   - 배포: GitHub Pages, Netlify Drop 등 무료 정적 호스팅
2. 트래픽 계획: 타깃이 모인 커뮤니티 2~3곳과 게시글 초안을 써준다(각 커뮤니티 규칙 준수, 광고 금지 커뮤니티는 제외). 광고를 쓸 경우 예산 상한을 사용자에게 받는다
3. 숫자가 모이면 `LAB fdt <id> --visits .. --clicks .. --signups .. --paid ..`
   - 기본 기준: 방문 200명 미만은 **표본 부족(hold)**, 가입률 5% 이상 **go**, 2~5% **retry**(헤드라인·가격 수정 후 재실험), 2% 미만 **drop**
   - 선결제·예약금이 1건이라도 있으면 강한 신호로 본다
   - 기준값은 `board.json`의 `settings`에서 바꾼다

**판정 (결정권자):** "유의미한 니즈가 확인됐는가?"
- 예 → `move <id> review --verdict go`
- 아니오(문제가 없음, 지불 의사 없음) → `move <id> dropped --verdict drop`
- 아직 모름 → 실험 자체가 유의미했는지 본다. 설계가 잘못됐으면 고쳐서 4단계를 다시 한다(`retry`)

## 5단계: 2일마다 리뷰 — 독점 가능성과 확장 가능성

`LAB due`로 오늘 리뷰할 아이디어를 뽑아 검토한다. 사용자가 "실험실 리뷰해줘"라고 하면 이 단계부터 한다.

**1-1 Easiness — 남이 쉽게 따라 할 수 있나** (`easy`: 5 = 따라 하기 어려움)
- 사업(사업 검토자): 같은 문제를 푸는 회사가 금방 할 수 있나, 사용자 확보 비용, 운영 비용, 규제·법적 이슈
- 기술(기술 검토자): 필요한 데이터를 구할 수 있나, 최신 AI로 가능한가, 1인 기술력으로 가능한가

**1-2 Moat — 해자** (`moat`)
- 네트워크 효과, 쌓이는 데이터, 독점 기술, 규모의 경제, 브랜드, 전환 비용 중 무엇이 생기나

**2. 확장 가능성** (`scale`)
- 시장 규모(작게 시작해도 커질 길이 있나), 인접 타깃·기능으로 넓힐 경로

**판정 (결정권자):** "독점 가능성과 확장 가능성이 있는가?"
- 예 → `move <id> done --verdict go --priority N`
- 아니오 → `move <id> dropped`
- 보완 필요 → 무엇을 보완할지 적고 `review`에 남긴다(다음 리뷰일이 2일 뒤로 잡힘)

## 한 바퀴 마무리

1. DONE 목록을 우선순위 순으로 표로 보여준다: 제목, P/S, FDT 가입률, easy/moat/scale, 이유 한 줄
2. 1순위는 `idea-blueprint`로 넘겨 설계도를 만든다
3. Drop 목록에서 "타깃만 바꾸면 살 수 있는 것"이 있으면 1단계에 새 아이디어로 다시 넣는다

## 대시보드

- `LAB serve` → 브라우저에서 칸반 보드가 열린다(`http://127.0.0.1:8765`)
- 카드를 눌러 P/S, 점수, FDT 숫자를 고치거나 단계를 옮기면 `lab/board.json`에 바로 저장된다
- 사용자가 대시보드에서 바꾼 내용은 다음 작업 전에 `LAB list`로 다시 읽어서 반영한다

## 보고 형식

매번 채팅 첫 줄에 깔때기 현황을 한 줄로 쓴다.
`Ideation 12 → Incubating 3 → Brainstorming 5 → Filtering 4 → 리뷰 2 → DONE 1 · Drop 9 · 병렬 6/10`
그다음 이번에 판정한 아이디어만 표로 보여주고, 사용자가 할 일 1개로 끝낸다.
