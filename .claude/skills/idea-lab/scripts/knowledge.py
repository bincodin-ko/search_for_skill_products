"""복리 학습 지식 파일 만들기 (보완 #16, 사용자 지시 2026-09-27: "발굴할수록 배수로 능력이 향상되게").

웨이브를 보내기 전에 메인이 실행한다. 보드 전체에서 세 가지를 뽑아 lab/knowledge/ 에 쓴다.
  titles.tsv   — id·단계·기법·제목·탈락 사유 요약 (발굴자가 grep: 중복 확인 + 왜 죽었는지 즉시 확인)
  patterns.md  — 살아남은 아이디어(4단계 이상)의 구조 카드 (SCAMPER·가정법의 씨앗 — 생존이 늘수록 씨앗도 는다)
  yield.md     — 기법·출처별 적중률(통과·보류율, 3단계 도달, 생존) (웨이브 배분에 쓴다 — 단 할당표 최소치는 지킨다)
사용: py -3 scripts/knowledge.py [board.json]
"""
import collections
import json
import pathlib
import sys

SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.cwd() / "lab" / "board.json")
OUT = SRC.parent / "knowledge"
OUT.mkdir(exist_ok=True)
board = json.loads(SRC.read_text(encoding="utf-8"))
ideas = board["ideas"]
ALIVE = {"filtering", "review", "done"}


def method(i):
    return i.get("origin") or (i.get("source") or "").split(":")[0] or "기타"


def reason(i):
    d = i.get("drop") or {}
    r = d.get("summary") or d.get("from") or ""
    if not r:
        for h in reversed(i.get("log") or []):
            if h.get("to") == "dropped":
                r = h.get("reason", "")
                break
    return " ".join(str(r).split())[:160]


# 1) titles.tsv
with open(OUT / "titles.tsv", "w", encoding="utf-8") as f:
    f.write("id\tstage\tmethod\ttitle\tdrop_type\tdrop_reason\n")
    for i in ideas:
        d = i.get("drop") or {}
        f.write("\t".join([i["id"], i["stage"], method(i), " ".join(i.get("title", "").split()),
                           d.get("type", ""), reason(i) if i["stage"] == "dropped" else ""]) + "\n")

# 2) patterns.md
alive = [i for i in ideas if i["stage"] in ALIVE]
lines = ["# 이긴 구조 카드 (자동 생성 — 손으로 고치지 말 것, 설명은 patterns_notes.md)",
         f"살아있는 {len(alive)}개. 발상법(특히 SCAMPER·가정법)은 이 구조를 **다른 대상·다른 거래 시점·다른 지불자**로 옮겨 독립 제품을 만든다. 같은 구매자·같은 시점이면 모듈.", ""]
for i in alive:
    rm = i.get("revenue_math") or {}
    pay = "💳 가치 기반" if (i.get("pay_pending") and not i["pay_pending"].get("proven")) else "지불 선례 있음"
    lines += [f"## {i['id']} {i['title']}",
              f"- 문제: {' '.join(str(i.get('p_code', '')).split())[:200]}",
              f"- 해법: {' '.join(str(i.get('s_code', '')).split())[:200]}",
              f"- 기법: {method(i)} · 지불: {pay} · 수익 모델: {rm.get('model', '?')} · 지불자: {rm.get('payer', '?')}",
              ""]
(OUT / "patterns.md").write_text("\n".join(lines), encoding="utf-8")

# 3) yield.md
stat = collections.defaultdict(lambda: collections.Counter())
for i in ideas:
    m = method(i)
    s = stat[m]
    s["n"] += 1
    reached3 = i["stage"] in ALIVE | {"brainstorming"} or any(h.get("to") == "brainstorming" for h in (i.get("log") or []))
    prefilter_drop = i["stage"] == "dropped" and not reached3
    s["pass"] += 0 if prefilter_drop else 1
    s["r3"] += 1 if reached3 else 0
    s["alive"] += 1 if i["stage"] in ALIVE else 0
rows = sorted(stat.items(), key=lambda kv: (-kv[1]["alive"], -kv[1]["r3"]))
out = ["# 기법·출처별 적중률 (자동 생성)", "",
       "| 기법·출처 | 후보 | 사전 필터 통과 | 3단계 도달 | 생존 | 생존율 |", "|---|---|---|---|---|---|"]
for m, s in rows:
    if s["n"] < 5 and not s["alive"]:
        continue
    out.append(f"| {m} | {s['n']} | {s['pass']} | {s['r3']} | {s['alive']} | {s['alive'] * 100 / s['n']:.1f}% |")
out += ["", "배분 규칙: 할당표 최소치(각 기법 6개)는 지키고, 남는 웨이브는 최근 생존율·3단계 도달률이 높은 칸에 더 준다(쏠림 상한 15개)."]
(OUT / "yield.md").write_text("\n".join(out), encoding="utf-8")
# 4) speed.md — 보완 #19: 웨이브별 속도(시간당 통과·보류, 통과·보류당 도구 호출)를 기법별로 누적
rl = OUT / "runlog.tsv"
sp = ["# 속도 기록 (자동 생성 — lab.py take/ingest가 runlog.tsv에 쌓음)", ""]
if rl.exists():
    recs = [dict(zip(rl.read_text(encoding="utf-8").splitlines()[0].split("\t"), line.split("\t")))
            for line in rl.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    by = collections.defaultdict(lambda: [0.0, 0, 0, 0, 0])
    for r in recs:
        if float(r.get("minutes") or 0) <= 0:
            continue  # 소요 시간이 없는 줄은 속도 계산에서 뺀다(take/ingest에 --minutes를 꼭 넣을 것)
        k = (r.get("kind", ""), r.get("method", ""))
        b = by[k]
        b[0] += float(r.get("minutes") or 0); b[1] += int(r.get("tools") or 0)
        b[2] += int(r.get("pass_hold") or 0); b[3] += int(r.get("alive_new") or 0); b[4] += 1
    sp += ["| 종류 | 기법 | 웨이브 수 | 분 | 통과·보류(조사는 pass) | 시간당 통과·보류 | 통과·보류당 도구 호출 | 새 생존 |", "|---|---|---|---|---|---|---|---|"]
    for (kind, m), (mins, tools, ph, alive_n, n) in sorted(by.items(), key=lambda kv: -(kv[1][2] / max(kv[1][0], 1))):
        sp.append(f"| {kind} | {m} | {n} | {mins:.0f} | {ph} | {ph * 60 / max(mins, 1):.1f} | {tools / max(ph, 1):.1f} | {alive_n} |")
    sp += ["", "읽는 법: 시간당 통과·보류가 오르고 통과·보류당 도구 호출이 내려가면 보완이 속도를 올린 것이다. 보완 점검마다 직전 묶음과 비교한다."]
(OUT / "speed.md").write_text("\n".join(sp), encoding="utf-8")

# 5) facts.tsv — 조사원이 확인한 사실(경쟁사 운영 여부·무료 공식 기능·법 조항·데이터 API) 공유 캐시. 파일만 보장(조사원이 덧붙임)
facts = OUT / "facts.tsv"
if not facts.exists():
    facts.write_text("분야\t사실(무엇이 있다·없다·된다·안 된다)\t근거 URL\t확인일\t확인자\n", encoding="utf-8")
print(f"knowledge: titles {len(ideas)} · patterns {len(alive)} · yield {len(rows)}행 · speed · facts → {OUT}")
