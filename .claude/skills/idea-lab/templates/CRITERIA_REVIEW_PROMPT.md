# 기준 변경 후 재검토 지시문

판정 기준이 바뀌었다(`C:\Users\김현빈\.claude\skills\idea-lab\references\research.md`의 need 욕망형·행동 증거·beatable 경쟁·해외 시장·운영 부담·수익 모델·왜 지금·fame 절을 먼저 읽는다). 아래 아이디어는 **옛 기준**으로 버려졌다. 새 기준으로 다시 보면 살아나는지 판단한다.
도구: WebSearch/WebFetch(아이디어당 검색 약 6회). **하위 에이전트 금지, 브라우저 도구 금지, 조사만(글쓰기·댓글·가입 금지).** 아이디어 하나 끝날 때마다 결과 한 줄을 즉시 덧붙인다.
각 아이디어는 `py -3 C:/Users/김현빈/.claude/skills/idea-lab/scripts/lab.py --board C:/Users/김현빈/ideas/lab/board.json show <id>`(PYTHONIOENCODING=utf-8)와 `C:\Users\김현빈\ideas\lab\ideas\<id>.md`(있으면)로 읽는다.

## 지시받은 관점으로 본다
- **beatable**: 버린 이유가 유료 경쟁사였다면 — 그 경쟁사의 가격(단위·날짜), 앱마켓·리뷰 사이트의 1~2점 리뷰 반복 불만(링크), 안 받아 주는 층(1인·소규모·특정 업종·특정 플랫폼). 이길 틈이 뚜렷하면 살리고, 같은 대상에게 무료·저가로 잘 풀고 있으면 유지
- **행동 증거**: 버린 이유가 불편 원문 부족이었다면 — 크몽·숨고에서 같은 작업을 **돈 주고 맡기는** 서비스·요청(판매 건수·가격), 템플릿 판매, 네이버 데이터랩·키워드 검색량, 우회법 글의 조회·스크랩 수, 앱 리뷰의 기능 요청 반복. 행동 증거 2건 이상 + 원문 1건이면 pain 관문 기준을 넘는다
- 해외 틈새로 더 크게 통하는지도 본다(`market`)
- 새로 걸리는 약점(운영 부담 월 40시간 초과, 수익 모델 불명)도 적는다

## 출력
`C:\Users\김현빈\ideas\lab\batches\<지시받은 파일>`에 아이디어마다 한 줄(JSON, `templates/RESEARCH_PROMPT.md`의 결과 형식과 같은 키를 쓰고 아래를 더한다):
`{"id":"i000","verdict":"revive|keep_dropped","need":3,"revenue":3,"fame":1,"tenx":3,"dist":3,"fit":3,"need_type":"pain","market":"kr","reason":"한 줄 사실 근거","competitors_beatable":[{"name":"","price":"","weakness":"리뷰 링크"}],"behavior_evidence":[{"what":"","url":""}],"pain_quotes":[{"quote":"","url":""}],"revenue_math":{"model":"subscription","formula":"","basis":""},"ops":{"hours_month":0,"human_work":"","automatable":true},"note":"카드 메모 2~4줄","login_sources":[]}`
- `revive`는 새 기준에서 need·수익성(max(revenue, fame)) 모두 3 이상이고 근거 링크가 있을 때만
- 링크·숫자는 실제로 확인한 것만
끝나면 revive만 한 줄 이유와 함께 100단어 이내로 돌려준다.
