> **먼저 `C:\Users\김현빈\.claude\skills\idea-lab\templates\CORE_RULES.md`를 읽는다.** (100개 묶음 깔때기 2단계 — 보완 #15)

# 묶음 1차 카드 선별

입력 파일의 후보(묶음 하나의 통과·보류 약 100개)를 **검색 없이 카드와 지식 파일만으로** 비교해 심층 조사할 순서를 정한다. 보드 수정 금지.
먼저 읽기: `C:\Users\김현빈\ideas\lab\knowledge\patterns.md`(살아남은 구조), `lessons.md`, `yield.md`. 카드마다 필요하면 `titles.tsv`를 grep(옛 탈락과 겹치는지).

## 할 일
1. **점수**(1~5, 카드 근거로만): 불편 크기·빈도 / 지불 근거(선례·value_evidence·유명세) / 1인 4주 제작 / 해자(데이터·한국 특유·법 지식) / 이긴 구조와 닮음 / 결정적 약점(무료 공식·운영 중 대형 경쟁·법)의 위험(높을수록 감점). `total` = 앞 다섯 합 − 위험
2. **묶기**: 같은 구매자·같은 구매 시점이면 한 카드로(`merge_into`), 살아 있는 아이디어의 부가 기능이면 `module_of`
3. **선정**: 상위 25~30개를 `pick`, 나머지는 `skip`. 분야 다양성(할당표: 소비자·대중·해외·B2B·크리에이터·게임·게이·회색)이 한쪽으로 쏠리지 않게 조정하되 점수를 크게 거스르지 않는다. 시간이 급한 후보(기회가 닫히는 중)는 `urgent: true`
4. **분야 묶음**: pick을 같은 분야·같은 확인 항목끼리 5~6개씩 `group`(예: "G1-외국인 행정", "G2-게임 소재")으로 나눈다 — 한 조사원이 한 그룹을 맡는다
5. **선별 보정**: skip 중 무작위 3개를 `calibration: true`로 표시(심층 조사해 선별 기준이 좋은 후보를 버리는지 잰다)

## 출력
`C:\Users\김현빈\ideas\lab\batches\<지시받은 출력 파일>`에 카드마다 한 줄: `{"id":"i000","total":0,"scores":{"pain":0,"pay":0,"build":0,"moat":0,"pattern":0,"risk":0},"decision":"pick|skip","group":"G1-...","urgent":false,"merge_into":"","module_of":"","calibration":false,"why":"한 줄"}`
끝나면 그룹별 pick 목록(id)과 urgent·merge·module만 한국어 150단어 이내로 돌려준다.
