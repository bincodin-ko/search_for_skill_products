import pathlib
"""idea-lab 보완 기능 전체 점검 (보드 복사본에서 — 실제 보드는 건드리지 않는다).
기준·lab.py·템플릿을 고친 뒤 반드시 실행: py -3 scripts/selftest.py [board.json]
실패가 0이어야 발굴을 다시 시작한다."""
import json, os, shutil, subprocess, sys, pathlib, tempfile

LAB = str(pathlib.Path(__file__).with_name("lab.py"))
SRC = sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path.cwd() / "lab" / "board.json")
W = pathlib.Path(tempfile.mkdtemp(prefix="labtest_"))
BOARD = W / "board.json"
shutil.copy(SRC, BOARD)
env = dict(os.environ, PYTHONIOENCODING="utf-8")
fails = []

def lab(*a, ok=True):
    r = subprocess.run([sys.executable, LAB, "--board", str(BOARD), *map(str, a)], capture_output=True, text=True, encoding="utf-8", env=env)
    if ok and r.returncode != 0:
        fails.append(f"CMD FAIL {a}: {r.stderr[-400:]}")
    return r.stdout + r.stderr

def board():
    return json.loads(BOARD.read_text(encoding="utf-8"))

def idea(iid):
    return next(i for i in board()["ideas"] if i["id"] == iid)

def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)

def write(name, rows):
    p = W / name
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return p

print("1) import: market·need_type·행동·왜지금·유명세·유입길 신호, 재확인 줄")
f = write("h.jsonl", [
    {"title": "테스트A 해외 욕망형 무료 도구", "p": "누가 불편", "s": "해결", "tags": ["B2C"], "signal": "s", "signal_url": "https://a.b",
     "source": "테스트", "prefilter": "pass", "market": "global", "need_type": "want", "behavior_signal": "공유 3만",
     "why_now": "2027 시행", "fame_signal": "비슷한 무료 도구 월 10만", "dist_path": "x"},
    {"title": "테스트B 재확인으로 떨어질 후보", "p": "p", "s": "s", "tags": ["B2B"], "signal": "s", "signal_url": "https://a.b", "source": "테스트", "prefilter": "pass"},
    {"title": "테스트B 재확인으로 떨어질 후보", "p": "p", "s": "s", "tags": ["B2B"], "signal": "s", "signal_url": "https://a.b", "source": "테스트",
     "prefilter": "drop: 재확인 무료 대체", "update_of": "테스트B 재확인으로 떨어질 후보"},
    {"title": "테스트C 한국 고통형", "p": "p", "s": "s", "tags": ["B2B"], "signal": "s", "signal_url": "https://a.b", "source": "테스트", "prefilter": "pass"},
    {"title": "테스트D 타이밍 대기 후보", "p": "p", "s": "s", "tags": ["B2B"], "signal": "s", "signal_url": "https://a.b", "source": "테스트", "prefilter": "pass"},
    {"title": "테스트E 유명세로 사는 후보", "p": "p", "s": "s", "tags": ["B2C"], "signal": "s", "signal_url": "https://a.b", "source": "테스트", "prefilter": "pass"},
])
out = lab("import", f)
ids = [i["id"] for i in board()["ideas"] if i["title"].startswith("테스트") and not i["title"].startswith("테스트F")]
A, Bb, C, D, E = ids[:5]
a = idea(A)
check(a["market"] == "global" and a.get("need_type") == "want", "A: market=global, need_type=want 저장")
check("행동 증거" in a["notes"] and "왜 지금" in a["notes"] and "유명세 경로" in a["notes"], "A: 행동·왜지금·유명세 신호가 메모에")
check(idea(Bb)["stage"] == "dropped" and "재확인 반영" in out, "B: 재확인 줄이 drop으로 반영")
check(not any("_imported_now" in i for i in board()["ideas"]), "임시 표식 _imported_now 제거")
f = write("h_wait.jsonl", [{"title": "테스트F 타이밍 대기 하베스트", "p": "p", "s": "s", "tags": ["B2B"], "signal": "s", "signal_url": "https://a.b",
     "source": "테스트", "prefilter": "hold: 시행령 확인", "why_now": "2027 시행", "revisit": "2027-01-15 (고시 확인)"}])
lab("import", f)
fi = next(i for i in board()["ideas"] if i["title"] == "테스트F 타이밍 대기 하베스트")
check(fi["stage"] == "ideation" and str(fi.get("hold", "")).startswith("타이밍 대기") and fi.get("next_review") == "2027-01-15", "F: 하베스트 hold+revisit → 타이밍 대기·재검토 날짜")

print("2) apply: fame·fame_math·수익모델·운영부담·유입길·wait·자동 Drop(수익성=max)")
f = write("r.jsonl", [
    {"id": A, "need": 3, "revenue": 1, "fame": 3, "tenx": 3, "dist": 3, "fit": 3, "verdict": "pass", "reason": "r", "need_type": "want", "market": "global",
     "fame_math": {"reach_goal": "월 1만", "basis": "b", "monetize": ["광고", "파생"], "run_cost": "월 5만"},
     "revenue_math": {"model": "ads", "formula": "월 PV 50만 × 6원", "basis": "b"},
     "ops": {"hours_month": 10, "human_work": "CS", "automatable": True},
     "dist_path": [{"way": "무료 계산기 검색 유입", "evidence": "월 2,400"}]},
    {"id": C, "need": 4, "revenue": 2, "tenx": 3, "dist": 3, "fit": 3, "verdict": "drop", "reason": "돈 안 냄"},
    {"id": D, "need": 3, "revenue": 3, "tenx": 3, "dist": 3, "fit": 3, "verdict": "wait", "why_now": "2027 규정 시행", "revisit": "2026-12-01", "reason": "증거 얇음"},
    {"id": E, "need": 3, "revenue": 2, "fame": 4, "tenx": 3, "dist": 3, "fit": 3, "verdict": "pass", "reason": "r"},
])
out = lab("apply", f)
a = idea(A)
check(a["stage"] == "brainstorming" and a["scores"].get("fame") == 3, "A: revenue 1이어도 fame 3이면 살아남음")
check("수익 계산(ads" in a["notes"] and "유명세 경로" in a["notes"] and "운영 부담" in a["notes"] and "직접 만드는 유입 길" in a["notes"], "A: 수익모델·유명세·운영부담·유입길 메모")
check(a.get("ops", {}).get("hours_month") == 10 and a.get("dist_path"), "A: ops·dist_path 필드 저장")
check(idea(C)["stage"] == "dropped", "C: need 4여도 revenue 2·fame 없음이면 자동 Drop")
check(idea(C).get("drop", {}).get("type") in ("small_market", "other", "competitor", "weak_evidence"), f"C: Drop 유형 분류됨({idea(C).get('drop', {}).get('type')})")
d = idea(D)
check(d["stage"] == "ideation" and str(d.get("hold", "")).startswith("타이밍 대기") and d.get("next_review") == "2026-12-01", "D: wait → 1단계 타이밍 대기 + 재검토 날짜")
check(idea(E)["stage"] == "brainstorming", "E: revenue 2 + fame 4 → 생존")
check("fame 4인데 fame_math가 없습니다" in out, "E: fame_math 없으면 경고")

print("3) audit: beatable·행동 증거·욕망형·유명세 선례·로그인 pain 유지")
f = write("a.jsonl", [
    {"id": A, "queries": list(range(6)), "competitors": [{"name": "비싼툴", "solves": "beatable", "weakness": "1점 리뷰 반복"}],
     "pain_quotes": [], "behavior_evidence": [1, 2, 3], "pay_evidence": [], "fame_evidence": [1], "verdict": "weak", "reason": "r"},
    {"id": E, "queries": list(range(6)), "competitors": [{"name": "무료툴", "solves": "yes"}], "pain_quotes": [{"quote": "q"}],
     "behavior_evidence": [1], "pay_evidence": [], "verdict": "kill", "reason": "무료 대체"},
])
lab("audit", f)
g = idea(A)["gate"]
check(g["compete"]["v"] == "pass" and "이길 틈" in g["compete"]["note"], "A: beatable 경쟁은 compete 통과 + 메모")
check(g["pain"]["v"] == "pass" and "욕망형" in g["pain"]["note"], "A: 욕망형은 행동 증거 3건으로 pain 통과")
check(g["pay"]["v"] == "pass" and "유명세 선례" in g["pay"]["note"], "A: 유명세 선례로 pay 통과")
g = idea(E)["gate"]
check(g["compete"]["v"] == "fail" and g["pain"]["v"] == "fail" and g["redteam"]["v"] == "fail", "E: 무료 대체(yes)·원문1+행동1·kill → 모두 fail")
# 원문 1 + 행동 2 규칙
f = write("a2.jsonl", [{"id": E, "queries": list(range(6)), "competitors": [], "pain_quotes": [{"quote": "q"}], "behavior_evidence": [1, 2],
                        "pay_evidence": [{"what": "x"}], "verdict": "survive", "reason": "r"}])
lab("audit", f)
check(idea(E)["gate"]["pain"]["v"] == "pass", "E: 원문 1 + 행동 증거 2 → pain 통과")

f = write("a3.jsonl", [{"id": C, "queries": list(range(6)), "competitors": [{"name": "무료툴", "solves": "yes"}], "pain_quotes": [], "verdict": "weak", "reason": "r",
                        "crowded_winnable": {"dist_edge": "GPTers 활동", "weakness": "리뷰 불만", "wedge": "1인 전용"}}])
lab("score", C, "dist=4")
lab("audit", f)
check(idea(C)["gate"]["compete"]["v"] == "pass" and "붐비는 시장 진입" in idea(C)["gate"]["compete"]["note"], "C: 무료 경쟁 있어도 crowded_winnable 3가지+dist 4 → compete 통과")
lab("score", C, "dist=3")
lab("audit", f)
check(idea(C)["gate"]["compete"]["v"] == "fail", "C: dist 3이면 crowded_winnable 있어도 compete 실패")
lab("move", C, "brainstorming", "--force", "--reason", "수익 구조 재검토 테스트", ok=False)
f = write("rev.jsonl", [{"id": C, "need": 4, "revenue": 3, "queries": list(range(6)), "competitors": [], "pain_quotes": [], "verdict": "weak", "reason": "r",
                        "revenue_math": {"model": "two_sided", "payer": "other_side", "formula": "병원 60곳 × 월 5만", "basis": "b"},
                        "payer_check": {"other_side": "병원 광고 가능", "government": "없음"}}])
out = lab("apply", f)
check("payer '" not in out and "model '" not in out and "지불자 other_side" in idea(C)["notes"] and bool(idea(C).get("payer_check")), "C: 새 수익 모델(two_sided)·지불자·지불자 점검 저장, 경고 없음")
out = lab("apply", write("rev2.jsonl", [{"id": C, "need": 4, "revenue": 3, "queries": list(range(6)), "competitors": [], "pain_quotes": [], "verdict": "weak", "reason": "r",
                        "revenue_math": {"model": "two_sided", "payer": "alien", "formula": "x", "basis": "b"}}]))
check("payer 'alien'" in out, "C: 잘못된 지불자는 경고")
n0 = len(board()["ideas"])
lab("import", write("wi.jsonl", [{"title": "테스트 가정법 아이디어", "p": "p", "s": "s", "tags": ["B2B"], "source": "가정법", "prefilter": "pass",
      "origin": "what_if", "what_if": {"target": "택시", "flip": "차를 하나도 안 가진다면", "consequence": "c", "solution": "s"}}]))
wi = board()["ideas"][-1]
check(len(board()["ideas"]) == n0 + 1 and wi.get("origin") == "what_if" and "💭 가정법" in wi["notes"] and "💭가정법" in lab("list"), "가정법 아이디어: origin 저장·메모·목록 표시")
check("whatif" in (pathlib.Path(LAB).parent / "dashboard.html").read_text(encoding="utf-8"), "대시보드에 💭 가정법 칩")
lab("import", write("sc.jsonl", [{"title": "테스트 SCAMPER 아이디어", "p": "p", "s": "s", "tags": ["B2B"], "source": "발상법:scamper", "prefilter": "pass",
      "origin": "scamper", "method": {"target": "가계부", "letter": "C", "change": "세금 신고 결합", "product": "x"}}]))
sc = board()["ideas"][-1]
check(sc.get("origin") == "scamper" and "🔀 SCAMPER" in sc["notes"] and "🔀SCAMPER" in lab("list"), "발상법(SCAMPER) 아이디어: origin·메모·목록 표시")
check("⚠ origin" in lab("import", write("bad.jsonl", [{"title": "테스트 잘못된 기법", "p": "p", "s": "s", "tags": ["B2B"], "prefilter": "pass", "origin": "magic"}])), "허락 안 된 발상법은 경고")
lab("move", C, "brainstorming", "--force", "--reason", "가치 기반 지불 테스트", ok=False)
ve_ok = {"loss_krw_year": 20000000, "loss_sources": ["https://a", "https://b"], "frequency": "연 2천 건", "decision_maker": "창업자", "price_krw_year": 300000}
lab("audit", write("va.jsonl", [{"id": C, "queries": list(range(6)), "competitors": [], "pain_quotes": [], "pay_evidence": [], "value_evidence": ve_ok, "verdict": "weak", "reason": "r"}]))
check(idea(C)["gate"]["pay"]["v"] == "pass" and idea(C).get("pay_pending") and "💳" in idea(C)["gate"]["pay"]["note"], "가치 기반 지불: 손실 10배·출처 2건·빈도·결정권자면 통과 + 💳 지불 검증 필요 표시")
ve_bad = dict(ve_ok, price_krw_year=5000000)
lab("audit", write("vb.jsonl", [{"id": C, "queries": list(range(6)), "competitors": [], "pain_quotes": [], "pay_evidence": [], "value_evidence": ve_bad, "verdict": "weak", "reason": "r"}]))
check(idea(C)["gate"]["pay"]["v"] == "fail", "가치 기반 지불: 가격이 연 손실의 10% 넘으면 실패")
lab("audit", write("vc.jsonl", [{"id": C, "queries": list(range(6)), "competitors": [], "pain_quotes": [], "pay_evidence": [{"x": 1}], "verdict": "weak", "reason": "r"}]))
check(idea(C)["gate"]["pay"]["v"] == "pass" and not idea(C).get("pay_pending"), "실제 지불 증거가 생기면 💳 표시 해제")
check("paytest" in (pathlib.Path(LAB).parent / "dashboard.html").read_text(encoding="utf-8"), "대시보드에 💳 지불 검증 필요 칸")
lab("move", C, "brainstorming", "--force", "--reason", "가치 기반 자동탈락 테스트", ok=False)
lab("apply", write("vd.jsonl", [{"id": C, "need": 4, "revenue": 2, "verdict": "pass", "reason": "r", "value_evidence": ve_ok}]))
check(idea(C)["stage"] == "brainstorming" and idea(C)["scores"]["revenue"] == 3, "가치 기반 증거가 있으면 revenue 2여도 자동 탈락하지 않음")
lab("move", C, "brainstorming", "--force", "--reason", "조사+레드팀 한 번에 테스트", ok=False)
comb = write("comb.jsonl", [{"id": C, "need": 4, "revenue": 3, "tenx": 3, "dist": 3, "fit": 3, "verdict": "pass", "reason": "조사 통과",
        "queries": list(range(6)), "competitors": [], "pain_quotes": [{"text": "a", "url": "u", "independent": True}] * 3, "pay_evidence": [{"x": 1}],
        "audit_verdict": "kill", "audit_reason": "레드팀이 죽임"}])
lab("apply", comb); lab("audit", comb)
check(idea(C)["gate"]["redteam"]["v"] == "fail" and "레드팀이 죽임" in idea(C)["gate"]["redteam"]["note"], "조사+레드팀 한 줄: audit_verdict로 레드팀 판정")
print("4) gate·move: 6항목 통과 전엔 4단계 불가, 통과하면 가능")
lab("verify", A, "--ok", "--note", "t")
out = lab("move", A, "filtering", "--reason", "t", ok=False)
check(idea(A)["stage"] == "brainstorming", "A: math·build 미통과면 4단계 이동 막힘")
lab("gate", A, "--set", "math=pass", "--note", "B 경로")
lab("gate", A, "--set", "build=pass", "--note", "ok")
lab("move", A, "filtering", "--reason", "t")
check(idea(A)["stage"] == "filtering", "A: 6항목 통과 후 4단계 이동")

print("5) rank·list·market·drops·stats·exceptions 명령")
out = lab("rank")
check(A in out, "rank: fame 경로 아이디어 순위 표시")
out = lab("list", "--stage", "ideation")
check("타이밍 대기" in out, "list: 타이밍 대기 사유 표시")
lab("market", C, "both")
check(idea(C)["market"] == "both", "market 명령")
out = lab("list", "--stage", "filtering")
check("🌍해외" in out, "list: 🌍해외 표시")
for cmd in (["drops", "--limit", "3"], ["stats", "--stages"], ["exceptions"], ["status"], ["gate", "coupang-leak"]):
    o = lab(*cmd)
    check("Traceback" not in o, f"{' '.join(cmd)} 실행")

out = lab("timing", "--date", "2027-01-20")
check("2027-01-15" in out, "timing: 재검토 날짜가 온 타이밍 대기 표시")
print("6) score 명령: fame 키, 경고")
out = lab("score", E, "need=3", "revenue=2", "fame=2")
check("수익성(max(revenue, fame)) ≤ 2" in out, "score: 수익성 ≤ 2 경고")

print("7) 템플릿 JSON 예시 문법")
import re
for t in ["RESEARCH_PROMPT.md"]:
    s = (pathlib.Path(LAB).parents[1] / "templates" / t).read_text(encoding="utf-8")
    m = re.search(r"`(\{\"id\":\"i000\".*?\})` \(한 줄\)", s)
    try:
        json.loads(m.group(1)); check(True, f"{t} 결과 예시 JSON 파싱")
    except Exception as e:
        check(False, f"{t} 결과 예시 JSON 파싱: {e}")

shutil.rmtree(W, ignore_errors=True)
print("\n결과:", "모두 통과" if not fails else f"{len(fails)}개 실패")
for f_ in fails:
    print(" -", f_)

sys.exit(1 if fails else 0)
