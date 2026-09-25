# 지불자(수익 구조) 재검토 지시문

너는 아이디어 실험실의 리서처다. 이 아이디어들은 **쓰는 사람이 돈을 안 낸다**는 이유로 버려졌다. 이번엔 다른 질문을 한다: **가치를 얻는 다른 누군가가 대신 내는 구조가 있나?**
먼저 `C:\Users\김현빈\.claude\skills\idea-lab\references\research.md`의 '수익 구조 카탈로그'(two_sided·sponsor·government·verification·data·white_label·usage·membership·embedded_fin·presale)와 법 제한 목록을 읽는다.
도구: WebSearch/WebFetch(아이디어당 검색 약 5회). **하위 에이전트 금지, 브라우저 도구 금지, 조사만(글쓰기·댓글·가입·연락 금지).** 보조 파일은 `scratchpad/<출력 파일 이름>/` 아래에만. 아이디어 하나 끝날 때마다 결과 한 줄을 즉시 덧붙인다.

각 아이디어는 `PYTHONIOENCODING=utf-8 py -3 C:/Users/김현빈/.claude/skills/idea-lab/scripts/lab.py --board C:/Users/김현빈/ideas/lab/board.json show <id>`와 `C:\Users\김현빈\ideas\lab\ideas\<id>.md`(있으면)로 읽는다. 왜 죽었는지(경쟁·무료 대체·법)가 지불 문제 말고도 있으면, 그 사유가 여전히 유효한지부터 본다 — 유효하면 바로 keep_dropped.

## 아이디어마다
1. **지불자 5가지 점검**(`payer_check`): other_side(반대편 업체·기관) / sponsor(자기 고객에게 무료로 주고 싶은 카드사·은행·보험·본사·협회·플랫폼) / government(바우처·지원사업 공급기업 등록 가능 여부 — 사업명·링크) / data_buyer(집계 데이터를 살 업계) / partner(화이트라벨로 자기 이름 붙여 줄 대행사·전문가). 각각 한 줄: 선례(국내 우선, 링크)·법적 가능 여부
2. 길이 있는 지불자로 `revenue_math`를 다시 쓴다(`model`, `payer`, `formula`, `price`, `customers_needed`, `basis`) — 그 지불자의 **지불 증거**(선례 가격·계약·공고)가 있어야 한다
3. 경쟁·생존 확인(월 사용자·회원 1만 이상 또는 검색 1페이지 독점만 막힘, 서비스 종료한 곳은 경쟁 아님)

## 출력
`C:\Users\김현빈\ideas\lab\batches\<지시받은 파일>`에 한 줄(JSON):
`{"id":"i000","verdict":"revive|keep_dropped","reason":"한 줄 사실 근거","need":4,"revenue":3,"tenx":3,"dist":3,"fit":3,"revenue_math":{"model":"two_sided","payer":"other_side","formula":"","price":"","customers_needed":0,"basis":""},"payer_check":{"other_side":"","sponsor":"","government":"","data_buyer":"","partner":""},"note":"카드 메모 2~4줄"}`
- `revive`는 지불자가 쓰는 사람이 아니거나 같더라도 새 구조이고, 그 지불자의 지불 증거 링크와 법적 길이 모두 있을 때만
- 링크·숫자는 실제로 확인한 것만. 끝나면 revive만 한 줄 이유와 함께 100단어 이내로 돌려준다.
