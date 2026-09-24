# LAB 명령 전체

`LAB` = `python "<스킬 폴더>/scripts/lab.py"` (Windows는 `py -3`). 표준 라이브러리만 쓴다. 보드는 현재 폴더의 `lab/board.json`, 다른 곳이면 `--board <경로>`.

## 보드·조회
- `LAB init` — 보드 생성 + `templates/`의 조사·하베스트 지시문을 `lab/batches/`로 복사
- `LAB list [--stage S]` / `LAB status`(보고 첫 줄) / `LAB show <id>` / `LAB due`(오늘 리뷰할 것) / `LAB serve`(대시보드)
- `LAB pending` — 3단계에서 점수가 없는 아이디어와 조사 파일만 남고 중단된 것(중단 복구용)
- `LAB stats` — 출처(하베스터)별 통과율 / `LAB stats --tags [--min N]` — 업종별 시도·생존 수와 고갈 분야
- `LAB exceptions` — 규칙 예외 후보와 피벗안(한 바퀴 마무리 때 사용자 검토용)
- `LAB gated [--all]` — 조사원이 "로그인 필요 출처"로 남긴 것 중 로그인 정보로 판정이 바뀔 수 있는 것(진행 중, 또는 증거 부족으로 2점이 된 것)만. 확인 후 `note`에 `[로그인 확인 날짜]`를 남기면 목록에서 빠진다
- `LAB rank [--apply]` — 평균(need·revenue·tenx·dist)→fit 순 추천 순서, 4단계 교체 후보 표시. `--apply`로 4단계 우선순위 적용(손 계산 금지)

## 추가·편집
- `LAB add --title .. --p .. --s .. [--from <원래 id>] [--tags B2B,외식]`
- `LAB import <harvest 파일(.json/.jsonl)>` — 하베스트 후보 일괄 추가. 비슷한 제목은 건너뜀, 신호가 있으면 2단계 통과, `prefilter: "drop: .."`는 Drop 기록, 출처·신호는 필드로 보존
- `LAB edit <id> [--title ..] [--p ..] [--s ..] --reason ".."` — 같은 아이디어 안에서 타깃·포지션을 좁힐 때(완전히 바뀌면 피벗). 제목·해결책을 바꾸면 관문 compete와 표본 검증이 초기화된다 → 경쟁 검색을 다시 한다
- `LAB note <id> --text ".."` 또는 `--file <파일>` — 카드 메모(조사 요약 5~8줄)
- `LAB bundle <이름> <id> <id> --reason ".."` / `LAB bundle --remove <id>` — 같은 고객·같은 엔진 묶음
- `LAB set key=value ..` — `founder`, `analytics`, `ga4_id`, `fdt_capacity`(0=제한 없음), `fdt_go_rate` 등

## 판정
- `LAB score <id> need=.. revenue=.. tenx=.. dist=.. fit=..` / `LAB score <id> --prelim easy=.. moat=.. scale=..`
- `LAB apply <resultN.json 또는 .jsonl>` — 조사 결과 일괄 반영(점수·가안·메모·수익 계산, need/revenue ≤ 2 자동 Drop, pass이거나 근거 있는 pivot만 예외 후보)
- `LAB drops [--type <유형>] [--md]` — Drop 사유 유형별 개수·목록, `--md`면 `lab/drops.md`(유형별 id·제목·이유 한 줄). 유형: merged·cant_build·legal·solved_free·competitor·one_off·small_market·weak_evidence·no_pain·other. Drop할 때 `LAB move <id> dropped --why <유형>`으로 직접 지정(생략하면 이유 문장으로 자동 분류)
- `LAB stats --stages` — 출처별 단계 정확도(하베스터 통과 → 선검증·조사·감사 탈락 → 생존, 하베스터 오판율)
- `LAB exceptions --md` — 예외 후보를 `lab/exceptions.md` 결정표로(사용자가 살림/피벗/버림 기입)
- `LAB gate <묶음 이름>` — 묶음 관문: 핵심은 6항목 전부, pain·pay는 묶음 증거 합산, 부가 아이디어는 compete·build만 통과하면 핵심의 부가 기능으로
- `LAB gate <id> [--set compete=pass pain=fail ..] [--note ..]` — 될놈 관문 6항목 보기·기록. 4단계 이동은 전부 pass여야 함
- `LAB audit <audit.jsonl>` — 레드팀 감사 결과 반영(compete·pain·pay·redteam 자동 판정, 메인이 같은 대상 기준으로 재확인)
- `LAB verify <id> --ok|--fail --note ".."` — 메인의 표본 검증 기록(4단계 이동에 필요)
- `LAB move <id> <stage> --reason ".." [--verdict go|drop|hold|retry] [--priority N] [--force]`
  - stage: `ideation` `incubating` `brainstorming` `filtering` `review` `done` `dropped`
  - `filtering`으로 옮기려면 3단계 점수와 표본 검증 통과가 필요하다

## 4단계 FDT
- `LAB fdt-scaffold <id|묶음>` — `templates/fdt.html`로 랜딩페이지 뼈대 생성(표본 검증 필요)
- `LAB fdt-start <id> --url ..` — 배포해 방문자를 보내기 시작할 때
- `LAB fdt <id> --visits .. --clicks .. --signups .. [--paid ..] [--url ..]` — 숫자 기록과 자동 판정

## 주의
- 보드는 항상 `LAB`으로 고친다. board.json 직접 편집 금지(대시보드 충돌 방지용 `rev`가 깨진다)
- Windows PowerShell 5.1: `$`가 든 문구는 작은따옴표. 인자 안 큰따옴표는 깨지므로 여러 줄·큰따옴표 문구는 파일로 넣는다(`--file`)
- 파이썬 heredoc으로 lab.py를 패치할 때 `"\n"`이 실제 줄바꿈으로 바뀌어 문법 오류가 난 적이 있다 — 패치 스크립트는 파일로 쓰고 raw 문자열을 쓴다
