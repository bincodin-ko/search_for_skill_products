#!/usr/bin/env python3
"""idea-lab board manager (standard library only).

The board lives in lab/board.json under the current folder. Claude and the
dashboard both read and write that one file. Research notes live next to it
in lab/ideas/<id>.md.

  init                          create lab/board.json
  add --title T --p P --s S     add an idea at the ideation stage (--from ID for a pivot, --tags a,b)
  import CANDIDATES.json        bulk-add harvested candidates (dedupe, stage 2, pre-filter drops)
  stats                         pass rate per discovery source (which harvester works)
  verify ID --ok|--fail --note  record the main session's spot-check of key evidence (needed for stage 4)
  exceptions                    list dropped rule-exception candidates and pivot ideas for user review
  pending                       stage-3 ideas without scores (and which have an interrupted research file)
  fdt-scaffold ID|BUNDLE        generate lab/fdt/<target>/index.html from the template (plans per idea, GA4, tracking)
  drops [--type T] [--md]        Drop reasons by type (competitor, solved_free, small_market, weak_evidence, ...)
  gate ID [--set k=pass ..]     the 6-item stage-4 gate (compete pain pay math build redteam)
  audit FILE                    apply red-team audit results (.jsonl) to the gate
  gated [--all]                 ideas whose research left login-gated sources; default = only ones login data could still change
  rank [--apply]                rank scored ideas (avg need·max(revenue,fame)·tenx·dist, then fit); --apply sets stage-4 priorities
  bundle NAME ID ID.. --reason  group ideas that share a customer/engine so one FDT page tests them all
  bundle --remove ID..          take ideas out of their bundle
  list [--stage S]              show ideas grouped by stage, with scores
  status                        one-line funnel summary for reports
  show ID                       print one idea as JSON (+ research file path)
  move ID STAGE --reason R      move an idea and log the decision
  score ID key=value ...        record scores (1-5); --prelim for provisional ones
  note ID --text T | --file F   set the idea's dashboard note
  edit ID [--title] [--p] [--s]  rewrite title / P-Code / S-Code (logged)
  fdt-start ID --url U          mark an FDT page as live (checks fdt_capacity)
  fdt ID --visits N ...         record fake-door-test numbers and judge them
  apply RESULT.json             apply a researcher batch result (scores, notes, auto-drop)
  due                           ideas in review whose 2-day review is due
  set key=value ...             change settings (analytics, ga4_id, thresholds...)
  serve [--port 8765]           open the dashboard (reads/writes board.json)
"""
import argparse
import datetime as dt
import difflib
import json
import os
import re
import socket
import sys
import tempfile
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STAGES = ["ideation", "incubating", "brainstorming", "filtering", "review", "done", "dropped"]
STAGE_LABELS = {
    "ideation": "1. 발굴 (Ideation) — 후보 모음·조사 전",
    "incubating": "2. 사전 확인 (Incubating)",
    "brainstorming": "3. 조사·관문 심사 중 (Brainstorming) — 검증 미완료",
    "filtering": "4. 검증 완료 · 가짜 문 테스트 대기 (Filtering/FDT)",
    "review": "5. 출시 후 2일마다 리뷰",
    "done": "완료 (DONE)",
    "dropped": "탈락 (Drop)",
}
SHORT_LABELS = {
    "ideation": "1 발굴", "incubating": "2 사전 확인", "brainstorming": "3 조사·심사 중",
    "filtering": "4 검증 완료·FDT 대기", "review": "5 리뷰", "done": "완료", "dropped": "탈락",
}
ACTIVE = ("filtering", "review")
VERDICTS = ["go", "drop", "hold", "retry"]
MARKETS = ["kr", "global", "both"]  # global/both는 대시보드에 🌍 해외 표시
NEED_TYPES = ["pain", "want"]  # need = 고통(불편·손실) 또는 욕망(재미·자랑·관계·호기심)
REVENUE_MODELS = ["subscription", "success_fee", "transaction", "lead", "one_time", "ads",
                  "two_sided", "sponsor", "government", "verification", "data", "white_label",
                  "usage", "membership", "embedded_fin", "presale", "other"]
# 발상법 출처(불만 원문 하베스트가 아닌 아이디어) — 대시보드·목록에 이 이름으로 표시. 새 기법은 사용자 허락 뒤에만 추가
ORIGINS = {
    "what_if": "💭 가정법", "scamper": "🔀 SCAMPER", "reverse": "🙃 역브레인스토밍",
    "unbundle": "✂️ 가치사슬 쪼개기·묶기", "lead_user": "🔬 극단 사용자", "trend_cross": "✖️ 두 흐름 교차",
    "jtbd": "🎯 해야 할 일(JTBD)", "constraint": "⛓️ 제약 추가",
    "ai_trend": "🤖 AI 신제품 활용",
}
PAYERS = ["user","other_side", "sponsor", "government", "data_buyer", "partner"]  # 누가 내나(references/research.md 수익 구조 카탈로그)
SCORE_KEYS = ["need", "revenue", "fame", "tenx", "dist", "fit", "easy", "moat", "scale"]
# fame = 무료라도 유명해져 돈이 되는 길(광고·파생 유료 제품·제휴·인수·홍보 채널). 수익성은 max(revenue, fame)로 본다
# need <= 2 또는 수익성(max(revenue, fame)) <= 2 -> auto drop. dist = 첫 고객에게 닿는 길, fit = 창업자 적합도(settings.founder 기준)
DEFAULT_SETTINGS = {
    "max_parallel": 10,
    "fdt_min_visits": 200,
    "fdt_go_rate": 0.05,
    "fdt_retry_rate": 0.02,
    "review_every_days": 2,
    "target_monthly_profit_krw": 3000000,
    "analytics": "",   # ga4 | umami | plausible (asked once, before the first FDT page)
    "ga4_id": "",      # G-XXXXXXXXXX
    "fdt_capacity": 0, # optional cap on live FDT pages at once; 0 = no limit (not asked by default)
    "founder": "",     # one-paragraph founder profile used for the fit score (asked once)
}
NUMERIC_SETTINGS = {k for k, v in DEFAULT_SETTINGS.items() if isinstance(v, (int, float))}
SCRIPT_DIR = Path(__file__).resolve().parent
ID_RE = re.compile(r"^i\d{3,}$")


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def board_path(args):
    return Path(args.board)


def research_path(board_file, idea_id):
    return Path(board_file).parent / "ideas" / f"{idea_id}.md"


class BoardError(Exception):
    pass


def read_board(path):
    if not path.exists():
        raise BoardError(f"{path} not found. Run: lab.py init")
    board = json.loads(path.read_text(encoding="utf-8"))
    board.setdefault("settings", {})
    for key, value in DEFAULT_SETTINGS.items():
        board["settings"].setdefault(key, value)
    board.setdefault("ideas", [])
    board.setdefault("rev", 0)
    return board


def load(path):
    try:
        return read_board(path)
    except BoardError as exc:
        sys.exit(str(exc))


# Drop 사유 유형 — 사용자가 한눈에 보도록 모든 Drop에 붙인다(순서 = 자동 분류 우선순위)
DROP_TYPES = {
    "merged": "다른 아이디어에 합침·중복",
    "cant_build": "만들 수 없음(API·약관·기술)",
    "legal": "법·자격·규제 문제",
    "solved_free": "이미 무료로 해결됨(플랫폼 기본·정부·범용 AI)",
    "competitor": "이미 자리 잡은 경쟁 제품",
    "one_off": "한 번 쓰고 끝남(반복 가치 없음)",
    "small_market": "문제를 가진 사람이 적거나 돈을 안 냄",
    "weak_evidence": "조사·증거 부족(원문·지불 증거 못 찾음)",
    "no_pain": "불편이 약함",
    "other": "기타",
}
_DROP_RULES = [
    ("merged", r"합침|중복|같은 아이디어|i\d{3}.{0,20}흡수|기능으로 합"),
    ("cant_build", r"공개 ?API|쓰기 API|API.{0,6}(없|부재|미제공|미지원|미전달|전용)|build 불가|제작 불가|스크래핑|계정 자동화|브라우저 자동화|기술 정확도"),
    ("legal", r"변호사법|세무사|노무사|행정사|법무사|자격 업무|전문 ?자격|의료행위|신용정보법|약관(상|위반| 위험)|불법|위법|규제 위험|개인정보 거래|자격이 필요|인증 영역"),
    ("one_off", r"한 번 (쓰고|고치면|하고|만들면)|1회성|일회성|평생 한두|한두 번|반복성 (약|없)|거의 안 바뀜"),
    ("solved_free", r"무료로 (제공|공개|안내|지원|해결|할 수|쓸 수)|무료 (앱|대체|도구|계산기|플랜|서비스|양식|기능|제공|번들)|기본 (기능|내장|제공|탑재)|기본으로|네이티브|(정부|공공|국토부|고용노동부|식약처|관세청|국세청|KISA|지자체|보건소|고용24|홈택스).{0,25}(무료|제공|안내)|범용 AI|AI 래퍼|플랫폼 자체|자체 (AI|메뉴)|AI 신기능|카카오모먼트AI|AI 사전검수|GPT만|오픈소스|도 무료|무료화|월 0원|무료 요금제|기본 [가-힣]{0,6} ?기능|로 충분|으로 충분|로 해결됨|solved_free|무료·저가|무료 등록으로|무료로 도움"),
    ("competitor", r"이미|경쟁|존재|제공 중|판매 중|운영 중|영업 중|다수|선점|앱 \d+개|제품 \d+개|기존 (유료|앱|도구|솔루션|제품|해결)|동일 (기능|패키지|목적)|같은 (기능|일|모델)|선검증 실패|포화|레드오션|솔루션.{0,10}(있|제공)|과 겹침|와 겹침|기존 (연동|관리비|[가-힣]{1,6} 앱)"),
    ("small_market", r"시장.{0,6}작|규모.{0,8}(작|미달|좁)|소수|대상.{0,8}(적|좁)|지불 (의사|의향).{0,4}약|돈을 (안|내지)|월 ?300만 불가|고객 0명|revenue 2|수익성 2|너무 좁|대상이.{0,25}(한정|해당 없|맞지 않)|해당 없음|지불 유인|구독 근거"),
    ("weak_evidence", r"원문.{0,4}(0건|없|못)|증거.{0,4}(없|부족|못|미충족)|확인 (못|안 ?됨)|못 찾|근거.{0,4}(부족|약|없|불충분)|미확인|미충족|사실 자체|하지 못|유추|간접 확인|검증하지|미확보|불확실|미확정|의무 대상 없|찾지 못"),
    ("no_pain", r"need 1|필요성 (1|2)|불편.{0,4}약"),
]


def drop_reason_text(idea):
    for l in reversed(idea.get("log") or []):
        if l.get("to") == "dropped" and l.get("reason"):
            return str(l["reason"])
    return ""


def classify_drop(idea):
    import re as _re
    reason = drop_reason_text(idea)
    text = reason + " " + str((idea.get("verified") or {}).get("note", ""))
    for key, pat in _DROP_RULES:
        if _re.search(pat, text):
            kind = key
            break
    else:
        sc = idea.get("scores") or {}
        if (sc.get("need") or 5) <= 2:
            kind = "no_pain"
        elif (money(sc) or 5) <= 2:
            kind = "small_market"
        else:
            kind = "other"
    summary = _re.sub(r"^\s*(선검증 실패|선검증|조사|보류 판정|보류 확인[^:]*|레드팀 감사 kill|레드팀 감사|레드팀|관문 [^:]*실패|사전 필터|하베스트 사전 필터|표본 검증 실패)\s*[:：]\s*", "", reason).strip()
    if len(summary) > 80:
        summary = summary[:78].rstrip() + "…"
    return kind, summary


def ensure_drop_info(board):
    """Drop 카드마다 사유 유형·한 줄 요약을 붙인다. 사람이 --why로 정한 것은 바꾸지 않는다."""
    for i in board["ideas"]:
        if i["stage"] != "dropped":
            continue
        d = i.get("drop") or {}
        if d.get("manual"):
            continue
        reason = drop_reason_text(i)
        if d.get("from") == reason and d.get("type") and d.get("type") != "other":
            continue  # other는 규칙이 늘면 다시 분류한다
        kind, summary = classify_drop(i)
        i["drop"] = {"type": kind, "summary": summary, "from": reason, "manual": False}


def save(path, board):
    """Write atomically and bump rev so a stale dashboard can't overwrite newer changes."""
    ensure_drop_info(board)
    validate(board)
    board["rev"] = int(board.get("rev", 0)) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".board-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    # Windows: the dashboard server may hold board.json open for a moment
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 9:
                os.remove(tmp)
                raise
            time.sleep(0.2)


def validate(board):
    if not isinstance(board.get("ideas"), list):
        raise ValueError("board.ideas must be a list")
    settings = board.get("settings", {})
    for key in NUMERIC_SETTINGS:
        if key in settings and not isinstance(settings[key], (int, float)):
            raise ValueError(f"settings.{key} must be a number")
    ids = set()
    for idea in board["ideas"]:
        if idea.get("stage") not in STAGES:
            raise ValueError(f"idea {idea.get('id')}: unknown stage {idea.get('stage')!r}")
        if not idea.get("id") or idea["id"] in ids:
            raise ValueError(f"missing or duplicate idea id {idea.get('id')!r}")
        ids.add(idea["id"])
        for field in ("scores", "prelim"):
            for key, value in (idea.get(field) or {}).items():
                if not isinstance(value, (int, float)) or not 1 <= value <= 5:
                    raise ValueError(f"idea {idea['id']}: {field}.{key} must be 1-5")


def find(board, idea_id):
    for idea in board["ideas"]:
        if idea["id"] == idea_id:
            return idea
    sys.exit(f"no idea with id {idea_id}")


def next_id(board):
    nums = [int(i["id"][1:]) for i in board["ideas"] if i["id"][1:].isdigit()]
    return f"i{max(nums, default=0) + 1:03d}"


def count_active(board):
    return sum(1 for i in board["ideas"] if i["stage"] in ACTIVE)


def log(idea, from_stage, to_stage, verdict, reason):
    idea.setdefault("log", []).append(
        {"at": now(), "from": from_stage, "to": to_stage, "verdict": verdict, "reason": reason}
    )
    idea["updated_at"] = now()


def judge_fdt(fdt, settings):
    """Return (verdict, message) for fake-door-test numbers."""
    visits = fdt["visits"]
    if visits < settings["fdt_min_visits"]:
        return "hold", f"표본 부족: 방문 {visits}명 < 기준 {settings['fdt_min_visits']}명. 트래픽을 더 모으세요"
    rate = fdt["signups"] / visits
    paid_note = f" · 선결제 {fdt['paid']}건(강한 신호)" if fdt.get("paid") else ""
    if rate >= settings["fdt_go_rate"]:
        return "go", f"가입률 {rate:.1%} ≥ {settings['fdt_go_rate']:.0%} → 통과{paid_note}"
    if rate >= settings["fdt_retry_rate"]:
        return "retry", f"가입률 {rate:.1%}: 애매함 → 헤드라인·가격을 바꿔 재실험{paid_note}"
    if fdt.get("paid"):
        return "retry", f"가입률 {rate:.1%}로 낮지만 선결제 {fdt['paid']}건 → 타깃을 좁혀 재실험"
    return "drop", f"가입률 {rate:.1%} < {settings['fdt_retry_rate']:.0%} → 수요 약함, Drop 권장"


def funnel_line(board):
    ideas = board["ideas"]
    n = {st: sum(1 for i in ideas if i["stage"] == st) for st in STAGES}
    pend = sum(1 for i in ideas if i["stage"] == "filtering" and i.get("pay_pending") and not (i["pay_pending"] or {}).get("proven"))
    parts = [f"{SHORT_LABELS[st]} {n[st] - (pend if st == 'filtering' else 0)}" for st in STAGES[:6]]
    parts.insert(4, f"4-b 💳 지불 검증 필요 {pend}")
    flow = " → ".join(parts)
    cap = board["settings"]["max_parallel"] or "∞"
    return f"{flow} · Drop {n['dropped']} · 병렬 {count_active(board)}/{cap}"


def cmd_init(args):
    path = board_path(args)
    if path.exists():
        print(f"{path} already exists")
        return 0
    save(path, {"version": 1, "rev": 0, "settings": dict(DEFAULT_SETTINGS), "ideas": []})
    (path.parent / "ideas").mkdir(exist_ok=True)
    batches = path.parent / "batches"
    batches.mkdir(exist_ok=True)
    for tpl in ("RESEARCH_PROMPT.md", "HARVEST_PROMPT.md"):
        src = SCRIPT_DIR.parent / "templates" / tpl
        if src.exists() and not (batches / tpl).exists():
            (batches / tpl).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"created {path} (+ lab/batches/ 지시문 템플릿)")
    return 0


def cmd_add(args):
    path = board_path(args)
    board = load(path)
    if args.parent:
        find(board, args.parent)
    idea = {
        "id": next_id(board),
        "title": args.title,
        "p_code": args.p or "",
        "s_code": args.s or "",
        "stage": "ideation",
        "priority": None,
        "scores": {},
        "prelim": {},
        "fdt": None,
        "notes": args.notes or "",
        "parent": args.parent,
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "market": args.market or "kr",
        "log": [],
        "created_at": now(),
        "updated_at": now(),
        "next_review": None,
    }
    board["ideas"].append(idea)
    save(path, board)
    origin = f"  (← {args.parent} 피벗)" if args.parent else ""
    print(f"added {idea['id']}  {idea['title']}{origin}")
    return 0


def cmd_list(args):
    path = board_path(args)
    board = load(path)
    stages = [args.stage] if args.stage else STAGES
    for stage in stages:
        ideas = [i for i in board["ideas"] if i["stage"] == stage]
        if not ideas:
            continue
        ideas.sort(key=lambda i: (i.get("priority") is None, i.get("priority") or 0))
        print(f"\n## {STAGE_LABELS[stage]} ({len(ideas)})")
        for i in ideas:
            pri = f"P{i['priority']}" if i.get("priority") else "  -"
            sc = " ".join(f"{k}{i['scores'][k]:g}" for k in SCORE_KEYS if k in i.get("scores", {}))
            extra = f"  [{sc}]" if sc else ""
            if (i.get("fdt_live") or {}).get("url") and i["stage"] == "filtering":
                extra += "  FDT진행"
            if i.get("fdt"):
                extra += f"  FDT:{i['fdt']['verdict']}"
            if research_path(path, i["id"]).exists():
                extra += "  조사✓"
            if i.get("parent"):
                extra += f"  ←{i['parent']}"
            if i.get("bundle"):
                extra += f"  [묶음:{i['bundle']}]"
            if i.get("market") in ("global", "both"):
                extra += "  🌍해외"
            if i.get("pay_pending") and not (i["pay_pending"] or {}).get("proven"):
                extra += "  💳지불검증필요"
            if i.get("origin") in ORIGINS:
                extra += "  " + ORIGINS[i["origin"]].replace(" ", "")
            if i.get("hold") and i["stage"] == "ideation":
                h = str(i["hold"])
                extra += f"  [{h[:60]}]" if h.startswith("타이밍 대기") else "  [보류: 빈틈 증거 확인 필요]"
            print(f"  {i['id']}  {pri:>4}  {i['title']}{extra}")
    cap = board["settings"]["fdt_capacity"]
    print(f"\n{funnel_line(board)} · FDT 진행 {len(live_fdts(board))}" + (f"/{cap}" if cap else ""))
    return 0


def cmd_status(args):
    print(funnel_line(load(board_path(args))))
    return 0


def cmd_show(args):
    path = board_path(args)
    idea = find(load(path), args.id)
    print(json.dumps(idea, ensure_ascii=False, indent=2))
    rp = research_path(path, args.id)
    print(f"\nresearch: {rp}" + ("" if rp.exists() else " (없음)"))
    return 0


def cmd_move(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    if args.stage in ACTIVE and idea["stage"] not in ACTIVE:
        active = count_active(board)
        cap = board["settings"]["max_parallel"]  # 0 = 제한 없음
        if cap and active >= cap and not args.force:
            sys.exit(f"병렬 실험이 이미 {active}개입니다(최대 {board['settings']['max_parallel']}). --force로 무시")
    if args.stage == "filtering" and idea["stage"] != "filtering":
        missing = [k for k in ("need", "revenue") if k not in idea.get("scores", {})]
        if missing and not args.force:
            sys.exit(f"3단계 점수({', '.join(missing)})가 없습니다. LAB score 먼저, 또는 --force")
        if not (idea.get("verified") or {}).get("ok") and not args.force:
            sys.exit("핵심 근거 표본 검증이 없습니다. 링크를 직접 열어 확인한 뒤 "
                     "LAB verify <id> --ok --note '..' 먼저, 또는 --force")
        bad = gate_missing(idea)
        if bad and not args.force:
            sys.exit("될놈 관문 미통과: " + ", ".join(bad) + " — LAB gate <id>로 확인, 또는 --force")
    from_stage = idea["stage"]
    idea["stage"] = args.stage
    if args.stage == "dropped" and getattr(args, "why", None):
        idea["drop"] = {"type": args.why, "summary": (args.reason or "")[:80], "from": args.reason or "", "manual": True}
    if args.priority is not None:
        idea["priority"] = args.priority
    if args.stage == "review":
        days = board["settings"]["review_every_days"]
        idea["next_review"] = (dt.date.today() + dt.timedelta(days=days)).isoformat()
    elif args.stage in ("done", "dropped"):
        idea["next_review"] = None
        if args.stage == "dropped":
            idea["priority"] = None
    log(idea, from_stage, args.stage, args.verdict, args.reason)
    save(path, board)
    print(f"{idea['id']}: {STAGE_LABELS[from_stage]} → {STAGE_LABELS[args.stage]}")
    return 0


def cmd_score(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    field = "prelim" if args.prelim else "scores"
    target = idea.setdefault(field, {})
    for pair in args.pairs:
        key, _, value = pair.partition("=")
        if not value:
            sys.exit(f"expected key=value, got {pair!r}")
        if key not in SCORE_KEYS:
            sys.exit(f"unknown score key {key!r}. use: {', '.join(SCORE_KEYS)}")
        score = float(value)
        if not 1 <= score <= 5:
            sys.exit(f"{key}: score must be 1-5")
        target[key] = score
    idea["updated_at"] = now()
    save(path, board)
    print(f"{field}: {json.dumps(target, ensure_ascii=False)}")
    s = idea.get("scores", {})
    if not args.prelim and (s.get("need", 5) <= 2 or (money(s) or 5) <= 2):
        print("⚠ need ≤ 2 또는 수익성(max(revenue, fame)) ≤ 2 → 3단계 자동 Drop 대상")
    return 0


def cmd_note(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    idea["notes"] = text.strip()
    idea["updated_at"] = now()
    save(path, board)
    print(f"{idea['id']}: 메모 {len(idea['notes'])}자 저장")
    return 0


def cmd_timing(args):
    """타이밍 대기·재검토 날짜가 있는 아이디어를 날짜순으로. --all이 아니면 오늘(또는 --date)까지 온 것만."""
    board = load(board_path(args))
    today = args.date or dt.date.today().isoformat()
    rows = sorted((str(i.get("next_review") or "9999"), i["id"], i["stage"], i["title"], str(i.get("hold") or ""))
                  for i in board["ideas"] if i.get("next_review") and i["stage"] != "dropped")
    due = [r for r in rows if args.all or r[0] <= today]
    print(f"재검토 {'전체' if args.all else today + '까지'}: {len(due)}개 (날짜 있는 것 전체 {len(rows)}개)")
    for d, iid, st, t, h in due:
        print(f"  {d}  {iid}  [{st}] {t}" + (f"\n        {h[:110]}" if h else ""))
    return 0


def cmd_market(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    idea["market"] = args.value
    idea["updated_at"] = now()
    save(path, board)
    print(f"{idea['id']}: market = {args.value}")
    return 0


def cmd_edit(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    changes = {k: v for k, v in (("title", args.title), ("p_code", args.p), ("s_code", args.s)) if v}
    if not changes:
        sys.exit("바꿀 항목(--title/--p/--s)이 없습니다")
    idea.update(changes)
    note = ""
    if "title" in changes or "s_code" in changes:
        # 범위·해결책이 바뀌면 경쟁 집합도 바뀐다(실측: i390을 여러 나라로 넓히자 Shopify Managed Markets·Passport가 새 경쟁자로 등장)
        g = idea.setdefault("gate", {})
        if (g.get("compete") or {}).get("v") == "pass":
            g["compete"] = {"v": "unknown", "note": "범위 수정으로 경쟁 재확인 필요", "at": now()}
        if (idea.get("verified") or {}).get("ok"):
            idea["verified"] = {"ok": False, "note": "범위 수정으로 표본 검증 다시 필요", "at": now()}
        note = " — 경쟁·표본 검증 초기화(다시 확인)"
    log(idea, idea["stage"], idea["stage"], None, f"{', '.join(changes)} 수정: {args.reason}{note}")
    save(path, board)
    print(f"{idea['id']}: {', '.join(changes)} 수정{note}")
    return 0


def live_fdts(board):
    return [i for i in board["ideas"] if i["stage"] == "filtering" and (i.get("fdt_live") or {}).get("url")]


def cmd_fdt_start(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    if idea["stage"] != "filtering":
        sys.exit(f"{idea['id']}는 4단계(filtering)가 아닙니다")
    live = [i for i in live_fdts(board) if i["id"] != idea["id"]]
    cap = board["settings"]["fdt_capacity"]
    if cap and len(live) >= cap and not args.force:
        sys.exit(f"이미 FDT {len(live)}개가 진행 중입니다(여력 {cap}개: {', '.join(i['id'] for i in live)}). "
                 f"하나를 끝내거나 --force")
    idea["fdt_live"] = {"url": args.url, "started_at": now()}
    log(idea, "filtering", "filtering", "hold", f"FDT 시작: {args.url}")
    save(path, board)
    print(f"{idea['id']}: FDT 시작 ({len(live) + 1}" + (f"/{cap})" if cap else "개 진행 중)"))
    return 0


def clamp_score(v):
    return min(5, max(1, int(round(float(v)))))


def norm_title(t):
    return re.sub(r"[\s·\-_/()·,.+]+", "", str(t)).lower()


def similar_idea(board, title, threshold=0.82):
    """Return an existing idea whose title is nearly the same, else None."""
    n = norm_title(title)
    for i in board["ideas"]:
        m = norm_title(i["title"])
        if n == m or (n and m and difflib.SequenceMatcher(None, n, m).ratio() >= threshold):
            return i
    return None


def cmd_import(args):
    """Bulk-add harvested candidates:
    [{title, p, s, tags:[..], signal, signal_url, source, prefilter:"pass"|"drop: <reason>", parent?}]
    Adds each at ideation, passes P/S clarity (stage 2) when p and s are present, and records
    pre-filter drops. Near-duplicate titles (vs board and within the file) are skipped."""
    path = board_path(args)
    board = load(path)
    rows = read_rows(args.file)
    added = skipped = dropped = 0
    for r in rows:
        title = str(r.get("title", "")).strip()
        if not title:
            continue
        dup = similar_idea(board, title)
        pf_new = str(r.get("prefilter", "")).strip()
        if dup and (r.get("update_of") or dup.get("_imported_now")) and not dup.get("scores") \
                and dup["stage"] in ("ideation", "incubating", "brainstorming") and pf_new:
            # 하베스터가 같은 파일에 덧붙인 재확인 줄: 나중 판정이 이긴다
            why = pf_new.split(":", 1)[-1].strip()
            if pf_new.lower().startswith("drop"):
                log(dup, dup["stage"], "dropped", "drop", "하베스터 재확인: " + why)
                dup["stage"] = "dropped"
                dropped += 1
            elif pf_new.lower().startswith("hold"):
                log(dup, dup["stage"], "ideation", "hold", "하베스터 재확인 보류: " + why)
                dup["stage"], dup["hold"] = "ideation", why
            print(f"{dup['id']}  재확인 반영 → {dup['stage']}: {title}")
            continue
        if dup:
            print(f"skip (비슷한 아이디어 {dup['id']} {dup['title']}): {title}")
            skipped += 1
            continue
        parent = r.get("parent")
        if parent and not any(i["id"] == parent for i in board["ideas"]):
            parent = None
        signal = str(r.get("signal", "")).strip()
        url = str(r.get("signal_url", "")).strip()
        note = f"[{r.get('source', '발굴')}] 출처 신호: {signal}" + (f"\n{url}" if url else "")
        if r.get("pay_signal"):
            note += f"\n지불 증거(출처 신호): {r['pay_signal']}"
        if r.get("gap_signal"):
            note += f"\n빈틈 증거(출처 신호): {r['gap_signal']}"
        if r.get("fame_signal"):
            note += f"\n유명세 경로(출처 신호): {r['fame_signal']}"
        idea = {
            "id": next_id(board), "title": title,
            "p_code": str(r.get("p", "")).strip(), "s_code": str(r.get("s", "")).strip(),
            "stage": "ideation", "priority": None, "scores": {}, "prelim": {}, "fdt": None,
            "notes": note, "parent": parent,
            "source": str(r.get("source", "")).strip(),
            "signal": signal, "signal_url": url,
            "tags": [str(t).strip() for t in r.get("tags", []) if str(t).strip()],
            "market": r.get("market") if r.get("market") in MARKETS else "kr",
            "log": [], "created_at": now(), "updated_at": now(), "next_review": None,
        }
        if r.get("need_type") in NEED_TYPES:
            idea["need_type"] = r["need_type"]
        origin = r.get("origin") or ("what_if" if isinstance(r.get("what_if"), dict) else None)
        if origin in ORIGINS:
            # 불만 원문이 아니라 발상법에서 출발한 아이디어 — 대시보드·목록에 기법 표시(templates/IDEATION_METHODS.md)
            idea["origin"] = origin
            detail = r.get("method") if isinstance(r.get("method"), dict) else (r.get("what_if") if isinstance(r.get("what_if"), dict) else {})
            idea["method"] = detail
            if origin == "what_if":
                idea["what_if"] = detail
            if detail:
                idea["notes"] += (f"\n{ORIGINS[origin]}: " + " → ".join(f"{v}" for v in detail.values() if v))
        elif r.get("origin"):
            print(f"⚠ origin '{r['origin']}'은 {list(ORIGINS)} 중 하나여야 합니다")
        if r.get("behavior_signal"):
            idea["notes"] += f"\n행동 증거(출처 신호): {r['behavior_signal']}"
        if r.get("why_now"):
            idea["why_now"] = str(r["why_now"])
            idea["notes"] += f"\n왜 지금(출처 신호): {r['why_now']}"
        board["ideas"].append(idea)
        idea["_imported_now"] = True
        added += 1
        pf = str(r.get("prefilter", "pass")).strip()
        rv = re.match(r"\s*(\d{4}-\d{2}-\d{2})", str(r.get("revisit") or ""))
        if (pf.lower().startswith("wait") or pf.lower().startswith("hold")) and rv and r.get("why_now"):
            # 타이밍 대기: 막 열리는 시장 — 재검토 날짜와 함께 1단계에 둔다(대시보드 '타이밍 대기' 칩)
            idea["hold"] = f"타이밍 대기 — {r['why_now']} (재검토 {rv.group(1)})"[:300]
            idea["next_review"] = rv.group(1)
            idea["notes"] += "\n" + idea["hold"] + (f"\n대기 중 확인할 것: {pf.split(':', 1)[-1].strip()}" if ":" in pf else "")
            log(idea, "ideation", "ideation", "hold", "타이밍 대기(하베스트): " + idea["hold"])
        elif pf.lower().startswith("hold"):
            # 불편·지불 증거는 있지만 독립 빈틈 증거가 로그인·앱 리뷰 뒤에 있는 후보: 1단계에 두고 메인이 Aside로 확인
            idea["hold"] = pf.split(":", 1)[-1].strip()
            idea["notes"] += "\n보류: 독립 빈틈 증거 필요 — " + idea["hold"]
            log(idea, "ideation", "ideation", "hold", "하베스트 보류: " + idea["hold"])
        elif pf.lower().startswith("drop"):
            idea["stage"] = "dropped"
            log(idea, "ideation", "dropped", "drop", "사전 필터: " + pf.split(":", 1)[-1].strip())
            dropped += 1
        elif idea["p_code"] and idea["s_code"] and (signal or url):
            log(idea, "ideation", "incubating", "go", "P/S 명확 · 출처 신호 있음")
            log(idea, "incubating", "brainstorming", "go", "P-S 명확성 통과 · 사전 필터 통과")
            idea["stage"] = "brainstorming"
        print(f"{idea['id']}  {idea['stage']:<13} {title}")
    for i in board["ideas"]:
        i.pop("_imported_now", None)
    save(path, board)
    print(f"added {added} (사전 필터 drop {dropped}), skipped {skipped} duplicates")
    print(funnel_line(board))
    return 0


GATE_KEYS = {
    "compete": "기능 문장 검색 6회 이상(한·영) + 경쟁표, 같은 대상에게 무료·저가로 푸는 제품 없음",
    "pain": "이해관계 없는 불편 원문 3건 이상(24개월 이내, 로그인 출처 포함)",
    "pay": "같은 대상이 지금 이 문제에 돈을 낸다(가격·단위·출처)",
    "math": "두 길 중 하나: A 직접 수익(월 300만 원 계산) 또는 B 유명세(1년 도달 목표 근거 + 수익 전환 길 2개 이상 선례 + 월 운영비) — 어느 쪽이든 첫 사용자 도달 채널 URL과 실제 규모(회원 수·방문자)를 note에 적는다",
    "build": "1인 바이브코딩으로 4주 안에 MVP 가능, 필수 API·제휴가 막혀 있지 않음",
    "redteam": "레드팀 감사(죽일 근거 찾기)에서 kill이 아님",
}


def gate_missing(idea):
    g = idea.get("gate") or {}
    return [k for k in GATE_KEYS if (g.get(k) or {}).get("v") != "pass"]


def cmd_gate(args):
    """될놈 관문: 4단계에 들어가려면 여섯 항목이 모두 pass여야 한다(평균 점수만으로는 못 들어간다)."""
    path = board_path(args)
    board = load(path)
    members = [i for i in board["ideas"] if i.get("bundle") == args.id and i["stage"] != "dropped"]
    if members and not any(i["id"] == args.id for i in board["ideas"]):
        return bundle_gate(args.id, members)
    idea = find(board, args.id)
    g = idea.setdefault("gate", {})
    for kv in args.set or []:
        k, _, v = kv.partition("=")
        if k not in GATE_KEYS or v not in ("pass", "fail", "unknown"):
            sys.exit(f"잘못된 값: {kv} (키: {', '.join(GATE_KEYS)} / 값: pass|fail|unknown)")
        g[k] = {"v": v, "note": args.note or "", "at": now()}
    if args.set:
        log(idea, idea["stage"], idea["stage"], "hold", "관문 기록: " + " ".join(args.set) + (f" — {args.note}" if args.note else ""))
        save(path, board)
    print(f"{idea['id']} {idea['title']}")
    for k, desc in GATE_KEYS.items():
        e = g.get(k) or {}
        mark = {"pass": "✓", "fail": "✗"}.get(e.get("v"), "?")
        print(f"  {mark} {k:8} {desc}" + (f"\n             └ {e['note']}" if e.get("note") else ""))
    miss = gate_missing(idea)
    print("관문 통과" if not miss else f"미통과: {', '.join(miss)}")
    return 0


def bundle_gate(name, members):
    """묶음 관문: 핵심(가장 앞선 단계·관문 통과가 많은 것)은 6항목 전부, 부가 아이디어는 compete·build만 통과하면 핵심의 부가 기능으로 싣는다.
    pain·pay는 같은 고객이라 묶음 전체의 증거를 합쳐 본다."""
    order = {"filtering": 0, "review": 0, "done": 0, "brainstorming": 1}
    def ok(i, k): return ((i.get("gate") or {}).get(k) or {}).get("v") == "pass"
    members = sorted(members, key=lambda i: (order.get(i["stage"], 2), -sum(ok(i, k) for k in GATE_KEYS)))
    core, extras = members[0], members[1:]
    print(f"묶음 '{name}' — 핵심 {core['id']} {core['title']}")
    for k in GATE_KEYS:
        pooled = k in ("pain", "pay") and any(ok(i, k) for i in members)
        mark = "✓" if ok(core, k) or pooled else "✗"
        print(f"  {mark} {k:8}" + ("  (묶음 증거 합산)" if pooled and not ok(core, k) else ""))
    for e in extras:
        fit = ok(e, "compete") and ok(e, "build")
        print(f"  부가 {e['id']} {e['title'][:30]} — {'실을 수 있음' if fit else '미확정(compete·build 확인 필요)'}")
    return 0


def value_check(ve):
    """가치 기반 지불 관문(사용자 승인 2026-09-25): 돈을 낸 선례가 없어도 '돈을 낼 만큼 가치 있는 문제'인지 숫자로 본다.
    ① 한 고객이 1년에 잃는 돈·시간(loss_krw_year)이 출처 2건 이상으로 확인되고 ② 얼마나 자주·몇 명(frequency)
    ③ 결제 결정권자와 예산(decision_maker) ④ 가격 가설(price_krw_year)이 연간 손실의 10% 이하(10배 가치)."""
    if not isinstance(ve, dict) or not ve:
        return False, ""
    try:
        loss = float(ve.get("loss_krw_year") or 0)
        price = float(ve.get("price_krw_year") or 0)
    except (TypeError, ValueError):
        loss = price = 0
    srcs = [s for s in (ve.get("loss_sources") or []) if str(s).strip()]
    miss = []
    if loss <= 0 or len(srcs) < 2:
        miss.append("연간 손실 금액·출처 2건")
    if not str(ve.get("frequency") or "").strip():
        miss.append("발생 빈도·대상 규모")
    if not str(ve.get("decision_maker") or "").strip():
        miss.append("결제 결정권자")
    if price <= 0 or (loss > 0 and price > loss * 0.1):
        miss.append("가격이 연간 손실의 10% 이하")
    if miss:
        return False, "가치 기반 미충족(" + ", ".join(miss) + ")"
    return True, f"가치 기반: 연 손실 ₩{loss:,.0f} vs 가격 ₩{price:,.0f}({price / loss:.0%}) · 출처 {len(srcs)}건"


def cmd_audit(args):
    """레드팀 감사 결과(.jsonl)를 반영: 경쟁·불편·지불·레드팀 네 항목을 증거 개수로 자동 판정한다."""
    path = board_path(args)
    board = load(path)
    n = 0
    for r in read_rows(args.file):
        idea = find(board, r["id"])
        comps = r.get("competitors") or []
        quotes = [q for q in r.get("pain_quotes") or [] if q.get("independent", True)]
        g = idea.setdefault("gate", {})
        solved = [c["name"] for c in comps if c.get("solves") == "yes"]
        # beatable = 같은 대상에게 이미 팔지만 비싸거나 1~2점 리뷰 불만이 반복되는 유료 제품 → 이길 틈(시장 증거), fail 아님
        beat = [c["name"] for c in comps if c.get("solves") == "beatable" and c.get("weakness")]
        note = (f"푸는 제품: {', '.join(solved)}" if solved else f"검색 {len(r.get('queries') or [])}회, 완전 대체 없음")
        if beat:
            note += f" · 이길 틈 있는 유료 경쟁: {', '.join(beat)}"
        cw = r.get("crowded_winnable") or {}
        crowded_ok = bool(solved) and all(str(cw.get(k) or "").strip() for k in ("dist_edge", "weakness", "wedge")) \
            and ((idea.get("scores") or {}).get("dist") or 0) >= 4
        if crowded_ok:
            note += f" · 붐비는 시장 진입(유통 우위: {cw['dist_edge']} / 약점: {cw['weakness']} / 첫 자리: {cw['wedge']})"
        g["compete"] = {"v": "pass" if len(r.get("queries") or []) >= 6 and (not solved or crowded_ok) else "fail", "note": note, "at": now()}
        prev_pain = g.get("pain") or {}
        if prev_pain.get("v") == "pass" and "로그인" in (prev_pain.get("note") or "") and len(quotes) < 3:
            # 메인이 로그인 출처로 채운 원문은 감사원(공개 검색만 가능)이 못 본다 — 덮어쓰지 않는다
            prev_pain["note"] = prev_pain.get("note", "") + f" (감사 공개 검색 원문 {len(quotes)}건, 로그인 확인 유지)"
        else:
            beh = r.get("behavior_evidence") or []
            want = (idea.get("need_type") or r.get("need_type")) == "want"
            ok = len(quotes) >= 3 or (len(quotes) >= 1 and len(beh) >= 2) or (want and len(beh) >= 3)
            g["pain"] = {"v": "pass" if ok else "fail", "note": f"독립 원문 {len(quotes)}건 · 행동 증거 {len(beh)}건" + (" (욕망형)" if want else ""), "at": now()}
        pay, fame_ev = r.get("pay_evidence") or [], r.get("fame_evidence") or []
        ve = r.get("value_evidence") or {}
        value_ok, value_note = value_check(ve)
        g["pay"] = {"v": "pass" if pay or fame_ev or value_ok else "fail",
                    "note": f"지불 증거 {len(pay)}건" + (f" · 유명세 선례 {len(fame_ev)}건" if fame_ev else "")
                            + (f" · {value_note}" if ve else ""), "at": now()}
        # 지불 선례 없이 '돈을 낼 만큼의 가치'로만 통과하면 가짜 문 테스트에서 결제 의사를 증명해야 한다
        if pay or fame_ev:
            idea.pop("pay_pending", None)
        elif value_ok:
            idea["pay_pending"] = {"basis": ve, "at": now()}
            g["pay"]["note"] += " → 💳 지불 검증 필요(FDT에서 선결제·가격 확인 신청으로 증명)"
        # 조사+레드팀 한 번에(사용자 승인 A): 조사 줄의 verdict(pass/drop)와 겹치지 않게 audit_verdict를 먼저 본다
        av = r.get("audit_verdict") or r.get("verdict")
        ar = r.get("audit_reason") or r.get("reason", "")
        g["redteam"] = {"v": "fail" if av == "kill" else "pass", "note": f"{av}: {ar}", "at": now()}
        idea["audit"] = r
        if r.get("login_sources"):
            idea["notes"] += "\n로그인 필요 출처: " + " / ".join(r["login_sources"])
        log(idea, idea["stage"], idea["stage"], "hold", f"레드팀 감사 {av}: {ar}")
        if av == "kill" and idea["stage"] == "brainstorming":
            # 보완 #13: 레드팀 kill인데 수익·필요 점수가 높아 apply 자동 탈락을 피한 카드가 3단계에 남던 문제
            idea["stage"], idea["priority"] = "dropped", None
            idea["drop"] = {"type": "weak_evidence", "summary": f"레드팀 kill: {ar}"[:80], "from": ar}
            log(idea, "brainstorming", "dropped", "drop", f"레드팀 kill: {ar}"[:500])
            print(f"  {idea['id']}: 레드팀 kill → 탈락")
        n += 1
    save(path, board)
    print(f"감사 {n}건 반영. `LAB gate <id>`로 항목별 확인")
    return 0


def cmd_verify(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    idea["verified"] = {"ok": bool(args.ok), "note": args.note, "at": now()}
    log(idea, idea["stage"], idea["stage"], "go" if args.ok else "hold",
        ("표본 검증 통과: " if args.ok else "표본 검증 실패: ") + args.note)
    save(path, board)
    print(f"{idea['id']}: 표본 검증 {'통과' if args.ok else '실패'}")
    return 0


def read_rows(file):
    """Read a result file: a JSON array (.json) or one JSON object per line (.jsonl).
    Later lines win for the same id, so a researcher can append corrections."""
    text = Path(file).read_text(encoding="utf-8")
    if str(file).endswith(".jsonl"):
        rows = {}
        for n, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                print(f"⚠ {file}:{n} JSON 오류 — 건너뜀")
                continue
            # id가 있는 결과 줄만 합친다(나중 줄이 이김). 하베스트 후보처럼 id가 없으면 줄마다 따로 둔다
            rows[r.get("id") or f"_line{n}"] = r
        return list(rows.values())
    return json.loads(text)


def cmd_pending(args):
    """Ideas waiting for stage-3 research: whether a research file exists (interrupted run)."""
    path = board_path(args)
    board = load(path)
    todo = [i for i in board["ideas"] if i["stage"] == "brainstorming" and not i.get("scores")]
    with_md = [i for i in todo if research_path(path, i["id"]).exists()]
    print(f"조사 대기 {len(todo)}개 (조사 파일은 있는데 점수 없음 {len(with_md)}개 — 중단된 조사)")
    for i in todo:
        mark = "md있음" if research_path(path, i["id"]).exists() else "      "
        print(f"  {i['id']}  {mark}  {i['title']}")
    return 0


def cmd_fdt_scaffold(args):
    import html
    path = board_path(args)
    board = load(path)
    target = args.target
    if ID_RE.match(target):
        ideas = [find(board, target)]
    else:
        ideas = [i for i in board["ideas"] if i.get("bundle") == target]
        if not ideas:
            sys.exit(f"'{target}'은 아이디어 id도, 묶음 이름도 아닙니다")
    ideas.sort(key=lambda i: (i.get("priority") is None, i.get("priority") or 0))
    unverified = [i["id"] for i in ideas if not (i.get("verified") or {}).get("ok")]
    if unverified and not args.force:
        sys.exit(f"표본 검증이 없는 아이디어가 있습니다: {', '.join(unverified)} (LAB verify 먼저, 또는 --force)")
    out = path.parent / "fdt" / target / "index.html"
    if out.exists() and not args.force:
        sys.exit(f"{out}가 이미 있습니다(덮어쓰려면 --force)")
    tpl = (SCRIPT_DIR.parent / "templates" / "fdt.html").read_text(encoding="utf-8")
    e = lambda x: html.escape(str(x or ""), quote=True)
    first = ideas[0]

    def price_of(i):
        rm = i.get("revenue_math") or {}
        m = re.search(r"(월|건당|연)?\s*₩?\s*[\d,]+\s*(원|만\s*원)?", str(rm.get("price", "")) or i.get("s_code", ""))
        return m.group(0).strip() if m else "TODO 가격"

    problems = "\n".join(
        f'        <div><h3>TODO 문제 {n}</h3><p>{e(i["p_code"])}</p></div>' for n, i in enumerate(ideas, 1))
    plans = "\n".join(
        f"""        <div class="plan">
          <h3>{e(i["title"])}</h3>
          <p class="who">{e(i["p_code"][:80])}</p>
          <div class="price" style="font-size:28px;font-weight:700">{e(price_of(i))}</div>
          <ul><li>TODO 핵심 기능 1</li><li>TODO 핵심 기능 2</li></ul>
          <a class="btn" href="#notify" data-cta="plan_{e(i["id"])}" data-plan="{e(i["id"])}">이 가격으로 알림 받기</a>
        </div>""" for i in ideas)
    page = (tpl.replace("{{TITLE}}", e(first["title"]))
               .replace("{{BRAND}}", e(first["title"] if len(ideas) == 1 else f"TODO 브랜드({target})"))
               .replace("{{HEADLINE}}", e(first["p_code"]))
               .replace("{{LEAD}}", e(first["s_code"]))
               .replace("{{PROBLEMS}}", problems)
               .replace("{{PLANS}}", plans)
               .replace("{{FDT_ID}}", e(target))
               .replace("{{GA4}}", e(board["settings"].get("ga4_id", "")))
               .replace("{{TALLY}}", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"만들었습니다: {out}")
    print("다음: ① design-router로 방향을 정해 스타일 토큰 교체 ② TODO(copy) 문구를 조사 파일의 불편 원문·빈틈 증거로 채움"
          " ③ Tally 폼 ID 입력 ④ 배포 후 LAB fdt-start <id> --url ..")
    return 0


GATED_RE = re.compile(r"로그인 필요 출처[:：]\s*(.+)")


def cmd_gated(args):
    """로그인 뒤 출처가 남은 아이디어. 로그인 정보는 불편·지불 증거를 '더할' 수만 있고 경쟁 제품을 없애지는 못하므로,
    기본값은 증거 부족으로 떨어진 것(need·revenue 중 최저가 정확히 2, 표본 검증 실패 아님)과 진행 중인 것만 보여 준다."""
    board = load(board_path(args))
    rows = []
    for i in board["ideas"]:
        m = GATED_RE.search(i.get("notes", ""))
        if not m or "[로그인 확인" in i.get("notes", ""):
            continue
        sc = i.get("scores", {})
        low = min(sc.get("need") or 0, money(sc) or 0)
        failed = (i.get("verified") or {}).get("ok") is False
        live = i["stage"] not in ("dropped", "done")
        if args.all or live or (low == 2 and not failed):
            rows.append((0 if live else 1, i["id"], i["stage"], sc.get("need"), sc.get("revenue"), i["title"], m.group(1).strip()[:90]))
    for _, iid, st, n, r, t, src in sorted(rows):
        print(f"{iid}  [{st}] need {n} revenue {r}  {t}\n      볼 곳: {src}")
    print(f"\n{len(rows)}개. 확인하면 `LAB note <id> --text \"[로그인 확인 날짜] ...\"`로 남긴다(다음 목록에서 빠진다)")
    return 0


def cmd_drops(args):
    """Drop을 사유 유형별로 요약: `LAB drops`(유형별 개수) / `--type weak_evidence`(목록) / `--md`(lab/drops.md)"""
    path = board_path(args)
    board = load(path)
    ensure_drop_info(board)
    drops = [i for i in board["ideas"] if i["stage"] == "dropped"]
    groups = {k: [] for k in DROP_TYPES}
    for i in drops:
        groups.setdefault(i["drop"]["type"], []).append(i)
    if args.md:
        out = ["# Drop 사유 정리", "", f"총 {len(drops)}개 · 자동 분류(`LAB move .. dropped --why <유형>`으로 바로잡을 수 있음)", "",
               "| 유형 | 개수 | 다시 볼 가치 |", "|---|---|---|"]
        revisit = {"weak_evidence": "있음 — 로그인 출처로 원문을 채우면 살아날 수 있음", "small_market": "피벗 시", "other": "확인 필요"}
        for k, label in DROP_TYPES.items():
            if groups.get(k):
                out.append(f"| {label} | {len(groups[k])} | {revisit.get(k, '낮음')} |")
        for k, label in DROP_TYPES.items():
            if not groups.get(k):
                continue
            out += ["", f"## {label} ({len(groups[k])})", "", "| id | 제목 | 이유 한 줄 |", "|---|---|---|"]
            for i in sorted(groups[k], key=lambda x: x["id"]):
                out.append(f"| {i['id']} | {i['title'][:40]} | {i['drop']['summary'].replace('|', '/')} |")
        target = path.parent / "drops.md"
        target.write_text("\n".join(out) + "\n", encoding="utf-8")
        save(path, board)
        print(f"{target} 작성 ({len(drops)}개)")
        return 0
    if args.type:
        for i in sorted(groups.get(args.type, []), key=lambda x: x["id"])[: args.limit]:
            print(f"{i['id']}  {i['title'][:36]}\n      → {i['drop']['summary']}")
        return 0
    print(f"Drop {len(drops)}개 — 사유 유형별")
    for k, label in DROP_TYPES.items():
        if groups.get(k):
            print(f"  {len(groups[k]):4}  {label}  ({k})")
    save(path, board)
    return 0


def money(s):
    """수익성 = 직접 수익(revenue)과 유명세 경로(fame) 중 높은 쪽. fame이 없으면 revenue."""
    r, f = s.get("revenue"), s.get("fame")
    vals = [v for v in (r, f) if v is not None]
    return max(vals) if vals else None


def rank_key(i):
    s = i.get("scores", {})
    vals = [s.get("need"), money(s), s.get("tenx"), s.get("dist")]
    vals = [v for v in vals if v is not None]
    avg = sum(vals) / len(vals) if vals else 0
    gate_ok = sum(1 for k in GATE_KEYS if ((i.get("gate") or {}).get(k) or {}).get("v") == "pass")
    return (-round(avg, 3), -gate_ok, -(s.get("fit") or 0), i["id"])


def cmd_rank(args):
    """Recommended order. Stage-4 ideas get priorities with --apply; stage-3 ideas that beat
    the weakest stage-4 idea are shown as swap candidates (the swap itself needs the user's OK)."""
    path = board_path(args)
    board = load(path)
    f = sorted([i for i in board["ideas"] if i["stage"] == "filtering"], key=rank_key)
    b = sorted([i for i in board["ideas"] if i["stage"] == "brainstorming" and i.get("scores")], key=rank_key)
    def fmt(i):
        miss = gate_missing(i)
        return (f"{i['id']}  평균 {-rank_key(i)[0]:.2f}  fit {i.get('scores', {}).get('fit', '-')}  "
                f"{'검증✓' if (i.get('verified') or {}).get('ok') else '미검증'}  "
                f"{'관문✓' if not miss else '관문✗(' + ','.join(miss) + ')'}  {i['title']}")
    print("## 4단계 추천 순서")
    for n, i in enumerate(f, 1):
        print(f"  P{n}  {fmt(i)}")
    worst = f[-1] if f else None
    cap = board["settings"]["max_parallel"]
    if cap:
        better = [i for i in b if worst is None or rank_key(i) < rank_key(worst)]
        free = cap - count_active(board)
        print(f"\n## 3단계 대기 중 4단계로 올릴 만한 것 (빈자리 {free}개)")
        better = better[: max(free, 3)]
    else:
        # 자리 제한 없음: 규칙(need·수익성 ≥ 3)을 통과한 3단계 아이디어는 모두 후보, 표본 검증이 관문
        better = [i for i in b if min(i["scores"].get("need", 0), money(i["scores"]) or 0) >= 3]
        print("\n## 3단계 대기 (자리 제한 없음 — 표본 검증 + 될놈 관문 6항목이 관문)")
    for i in better:
        print(f"  {fmt(i)}")
    if not better:
        print("  없음")
    if args.apply:
        for n, i in enumerate(f, 1):
            if i.get("priority") != n:
                i["priority"] = n
                log(i, "filtering", "filtering", "hold", f"LAB rank: 우선순위 P{n}(평균·fit 순)")
        save(path, board)
        print("\n4단계 우선순위를 적용했습니다")
    return 0


def cmd_exceptions(args):
    board = load(board_path(args))
    rows = []
    for i in board["ideas"]:
        if i["stage"] != "dropped" or i.get("domain_off") or i.get("exception_decision"):
            continue
        reasons = [str(l.get("reason", "")) for l in i.get("log", [])]
        flagged = [x for x in reasons if "규칙 예외 후보" in x]
        if not flagged:
            continue
        pivot = ""
        for x in reversed(reasons):
            if "피벗안:" in x:
                pivot = x.split("피벗안:", 1)[1].split(" · ⚑")[0].strip()
                break
        s = i.get("scores", {})
        rows.append((i["id"], s.get("need", "-"), s.get("revenue", "-"), s.get("fit", "-"), i["title"], pivot))
    if not rows:
        print("예외 후보 없음")
        return 0
    print("id     need rev fit  제목 → 피벗안")
    for r in rows:
        print(f"{r[0]:<6} {r[1]!s:>4} {r[2]!s:>3} {r[3]!s:>3}  {r[4]}" + (f"\n       → {r[5][:120]}" if r[5] else ""))
    print(f"\n{len(rows)}개. 살리려면: LAB move <id> brainstorming --reason '사용자 예외 승인: ..' 또는 피벗이면 LAB add --from <id>")
    if getattr(args, "md", False):
        path = board_path(args)
        out = ["# 규칙 예외 후보 — 사용자 결정", "",
               "수익성·필요성 2 이하라 규칙상 Drop됐지만 조사원이 살릴 만하다고 본 것. '결정' 칸에 살림/피벗/버림을 적어 주면 메인이 반영한다.", "",
               "| id | need | rev | fit | 제목 | 피벗안 | 결정 |", "|---|---|---|---|---|---|---|"]
        for r in rows:
            out.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4][:30]} | {r[5][:90].replace('|', '/')} |  |")
        target = path.parent / "exceptions.md"
        target.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"{target} 작성")
    return 0


def cmd_bundle(args):
    path = board_path(args)
    board = load(path)
    if args.remove:
        for iid in args.ids:
            idea = find(board, iid)
            old = idea.pop("bundle", None)
            log(idea, idea["stage"], idea["stage"], None, f"묶음 해제: {old}")
        save(path, board)
        print(f"묶음 해제: {', '.join(args.ids)}")
        return 0
    if not args.name or len(args.ids) < 2:
        sys.exit("사용법: LAB bundle <이름> <id> <id> [..] --reason '..' (2개 이상)")
    if not args.reason:
        sys.exit("--reason이 필요합니다(왜 같은 FDT로 검증할 수 있나: 같은 고객/같은 엔진)")
    for iid in args.ids:
        idea = find(board, iid)
        idea["bundle"] = args.name
        log(idea, idea["stage"], idea["stage"], None, f"묶음 '{args.name}': {args.reason}")
    save(path, board)
    print(f"묶음 '{args.name}': {', '.join(args.ids)}")
    return 0


def cmd_stats(args):
    """Funnel per discovery source: how many candidates survived each gate."""
    board = load(board_path(args))
    if args.tags:
        return stats_by_tag(board, args.min)
    if args.stages:
        return stats_by_stage(board)
    rows = {}
    for i in board["ideas"]:
        src = i.get("source") or "직접 추가"
        r = rows.setdefault(src, {"후보": 0, "사전필터": 0, "조사drop": 0, "3단계": 0, "4단계+": 0, "예외후보": 0})
        r["후보"] += 1
        reasons = [str(l.get("reason", "")) for l in i.get("log", [])]
        if any(x.startswith("사전 필터:") for x in reasons):
            r["사전필터"] += 1
        elif i["stage"] == "dropped":
            r["조사drop"] += 1
        elif i["stage"] in ("filtering", "review", "done"):
            r["4단계+"] += 1
        elif i["stage"] == "brainstorming" and i.get("scores"):
            r["3단계"] += 1
        if i["stage"] == "dropped" and any("규칙 예외 후보" in x for x in reasons):
            r["예외후보"] += 1
    cols = ["후보", "사전필터", "조사drop", "3단계", "4단계+", "예외후보"]
    print(f"{'출처':<16}" + "".join(f"{c:>8}" for c in cols) + "   통과율")
    for src, r in sorted(rows.items(), key=lambda kv: -kv[1]["후보"]):
        passed = r["3단계"] + r["4단계+"]
        print(f"{src:<16}" + "".join(f"{r[c]:>8}" for c in cols) + f"   {passed / r['후보']:.0%}")
    return 0


def stats_by_stage(board):
    """단계별 정확도: 하베스터가 통과시킨 것 중 메인 선검증·조사·감사에서 몇 개가 틀렸나(출처별)."""
    rows = {}
    for i in board["ideas"]:
        src = i.get("source") or "직접 추가"
        r = rows.setdefault(src, {"후보": 0, "하베스터통과": 0, "선검증탈락": 0, "조사탈락": 0, "감사·관문탈락": 0, "생존": 0})
        r["후보"] += 1
        reasons = [str(l.get("reason", "")) for l in i.get("log", [])]
        if any(x.startswith("사전 필터") for x in reasons):
            continue
        r["하베스터통과"] += 1
        vnote = str((i.get("verified") or {}).get("note", ""))
        if (i.get("verified") or {}).get("ok") is False and ("선검증" in vnote or "보류" in vnote):
            r["선검증탈락"] += 1
        elif i["stage"] == "dropped" and any(x.startswith(("레드팀", "관문", "될놈 관문")) for x in reasons):
            r["감사·관문탈락"] += 1
        elif i["stage"] == "dropped":
            r["조사탈락"] += 1
        else:
            r["생존"] += 1
    cols = ["후보", "하베스터통과", "선검증탈락", "조사탈락", "감사·관문탈락", "생존"]
    print(f"{'출처':<16}" + "".join(f"{c:>10}" for c in cols) + "  하베스터 오판율")
    for src, r in sorted(rows.items(), key=lambda kv: -kv[1]["후보"]):
        wrong = r["선검증탈락"] + r["조사탈락"] + r["감사·관문탈락"]
        rate = f"{wrong / r['하베스터통과']:.0%}" if r["하베스터통과"] else "-"
        print(f"{src:<16}" + "".join(f"{r[c]:>10}" for c in cols) + f"  {rate}")
    print("\n하베스터 오판율 = 하베스터가 통과시킨 것 중 메인 선검증·조사·감사에서 떨어진 비율. 높은 출처는 선검증을 더 엄하게")
    return 0


def stats_by_tag(board, minimum):
    """Saturation map: per tag (industry/area), how many ideas were tried and how many survived."""
    rows = {}
    for i in board["ideas"]:
        for t in i.get("tags") or []:
            if t in ("B2B", "B2C"):
                continue
            r = rows.setdefault(t, [0, 0])
            r[0] += 1
            if i["stage"] in ("brainstorming", "filtering", "review", "done") and i.get("scores"):
                r[1] += 1
    items = sorted(((t, n, ok) for t, (n, ok) in rows.items() if n >= minimum), key=lambda x: (-x[1], x[0]))
    print(f"{'태그':<14}{'후보':>6}{'생존':>6}   상태")
    saturated = []
    for t, n, ok in items:
        state = "고갈(피할 것)" if n >= 8 and ok == 0 else ("얕음" if n < 4 else "")
        if state.startswith("고갈"):
            saturated.append(t)
        print(f"{t:<14}{n:>6}{ok:>6}   {state}")
    if saturated:
        print(chr(10) + "하베스터에 넘길 고갈 분야: " + ", ".join(saturated))
    return 0


def cmd_apply(args):
    """Apply a researcher batch result: [{id, need, revenue, tenx, dist?, fit?, easy, moat, scale,
    verdict, reason, pivot?, note?, login_needed?}]. Only ideas still in brainstorming are touched."""
    path = board_path(args)
    board = load(path)
    rows = read_rows(args.file)
    applied = dropped = 0
    for r in rows:
        idea = next((i for i in board["ideas"] if i["id"] == r.get("id")), None)
        if not idea:
            continue
        if idea["stage"] in ("ideation", "incubating"):
            # 보류·적체 후보를 조사원에게 바로 보낸 경우: 조사 결과가 곧 빈틈 확인이므로 3단계로 올려 반영한다
            # (보완 #12: hold 표시가 없는 적체 카드도 매번 손으로 옮기던 문제)
            log(idea, idea["stage"], "brainstorming", "go", "발굴 단계 후보 조사 결과 반영")
            idea["stage"] = "brainstorming"
        if idea["stage"] != "brainstorming":
            print(f"  건너뜀 {idea['id']}: 단계가 {idea['stage']}(3단계가 아님)")
            continue
        idea.setdefault("scores", {}).update(
            {k: clamp_score(r[k]) for k in ("need", "revenue", "fame", "tenx", "dist", "fit") if r.get(k) is not None})
        idea.setdefault("prelim", {}).update(
            {k: clamp_score(r[k]) for k in ("easy", "moat", "scale") if r.get(k) is not None})
        note = [f"[3단계 조사 {dt.date.today().isoformat()}] 상세: lab/ideas/{idea['id']}.md", str(r.get("note", "")).strip()]
        if r.get("pivot"):
            note.append(f"피벗안: {r['pivot']}")
        if r.get("login_needed"):
            note.append("로그인 필요 출처: " + ", ".join(map(str, r["login_needed"])))
        kept = [l for l in str(idea.get("notes", "")).splitlines() if "출처 신호" in l or l.startswith("http")]
        idea["notes"] = "\n".join(x for x in note + kept if x)
        idea["research_verdict"] = r.get("verdict", "")
        for k, allowed in (("need_type", NEED_TYPES), ("market", MARKETS)):
            if r.get(k) in allowed:
                idea[k] = r[k]
        if isinstance(r.get("crowded_winnable"), dict) and any(r["crowded_winnable"].values()):
            idea["crowded_winnable"] = r["crowded_winnable"]
            idea["notes"] += "\n붐비는 시장 진입 근거: " + " / ".join(f"{k}: {v}" for k, v in r["crowded_winnable"].items() if v)
        if r.get("dist_path"):
            idea["dist_path"] = r["dist_path"]
            idea["notes"] += "\n직접 만드는 유입 길: " + " / ".join(
                f"{d.get('way', '')}({d.get('evidence', '')})" if isinstance(d, dict) else str(d) for d in r["dist_path"])
        if r.get("ops"):
            idea["ops"] = r["ops"]  # 1인 운영 부담: {"hours_month":..,"human_work":"..","automatable":..}
            idea["notes"] += f"\n운영 부담: 월 {r['ops'].get('hours_month', '?')}시간 · {r['ops'].get('human_work', '')}"
        if r.get("why_now"):
            idea["why_now"] = str(r["why_now"])
            idea["notes"] += f"\n왜 지금: {r['why_now']}"
        rm = r.get("revenue_math")
        if isinstance(rm, dict) and rm:
            idea["revenue_math"] = rm
            model = rm.get("model", "subscription")
            if model not in REVENUE_MODELS:
                print(f"⚠ {idea['id']}: revenue_math.model '{model}'은 {REVENUE_MODELS} 중 하나여야 합니다")
            payer = rm.get("payer", "user")
            if payer not in PAYERS:
                print(f"⚠ {idea['id']}: revenue_math.payer '{payer}'은 {PAYERS} 중 하나여야 합니다")
            idea["notes"] += (f"\n수익 계산({model}, 지불자 {payer}): {rm.get('formula') or ('가격 ' + str(rm.get('price', '?')) + ' × 필요 고객 ' + str(rm.get('customers_needed', '?')))}"
                              f" = 월 300만 원 · 근거: {rm.get('basis', '')}")
        elif idea["scores"].get("revenue", 0) >= 3:
            print(f"⚠ {idea['id']}: revenue {idea['scores']['revenue']}인데 revenue_math가 없습니다(조사원에게 보완 요청)")
        if r.get("payer_check"):
            idea["payer_check"] = r["payer_check"]
            pc = r["payer_check"]
            idea["notes"] += "\n지불자 점검: " + (" / ".join(f"{k}: {v}" for k, v in pc.items()) if isinstance(pc, dict) else str(pc))
        fm = r.get("fame_math")
        if isinstance(fm, dict) and fm:
            idea["fame_math"] = fm
            idea["notes"] += (f"\n유명세 경로: 1년 목표 {fm.get('reach_goal', '?')} · 근거 {fm.get('basis', '')}"
                              f" · 수익 전환 {', '.join(map(str, fm.get('monetize', [])))} · 월 운영비 {fm.get('run_cost', '?')}")
        elif idea["scores"].get("fame", 0) >= 3:
            print(f"⚠ {idea['id']}: fame {idea['scores']['fame']}인데 fame_math가 없습니다(조사원에게 보완 요청)")
        idea["updated_at"] = now()
        applied += 1
        sc = idea["scores"]
        if r.get("verdict") == "wait" and r.get("why_now"):
            # 타이밍 대기: 막 열리는 시장이라 지금은 증거가 얇다 — 버리지 않고 재검토 날짜와 함께 1단계 보류
            when = str(r.get("revisit") or (dt.date.today() + dt.timedelta(days=60)).isoformat())
            idea["hold"] = f"타이밍 대기 — {r['why_now']} (재검토 {when})"
            idea["next_review"] = when
            log(idea, "brainstorming", "ideation", "hold", "타이밍 대기: " + str(r.get("reason", ""))[:300])
            idea["stage"] = "ideation"
            continue
        vok, vnote = value_check(r.get("value_evidence") or {})
        if vok and (money(sc) or 5) <= 2 and sc.get("need", 5) >= 3:
            # 가치 기반 지불(연 손실 ≥ 가격 10배, 출처 2건)이 확인되면 선례가 없어 revenue가 낮게 매겨졌어도 자동 탈락시키지 않는다
            sc["revenue"] = 3
            idea["notes"] += f"\n수익성 3으로 조정: {vnote} — 💳 FDT에서 결제 의사 확인 필요"
        if sc.get("need", 5) <= 2 or (money(sc) or 5) <= 2:
            reason = f"조사: {r.get('reason', '')}"
            if r.get("pivot"):
                reason += f" · 피벗안: {r['pivot']}"
            # 예외 후보는 조사원이 pass라고 했거나, 피벗안에 새 타깃의 근거 링크가 있을 때만
            if r.get("verdict") == "pass" or (r.get("verdict") == "pivot" and r.get("pivot_evidence")):
                reason += " · ⚑ 규칙 예외 후보(조사원은 " + r["verdict"] + ")"
                if r.get("pivot_evidence"):
                    reason += f" · 피벗 근거: {r['pivot_evidence']}"
            idea["stage"], idea["priority"] = "dropped", None
            log(idea, "brainstorming", "dropped", "drop", reason[:500])
            dropped += 1
    save(path, board)
    print(f"applied {applied}, auto-dropped {dropped}")
    print(funnel_line(board))
    return 0


def cmd_fdt(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    if args.visits <= 0:
        sys.exit("visits must be > 0")
    if min(args.clicks, args.signups, args.paid) < 0:
        sys.exit("counts must be >= 0")
    if args.signups > args.visits:
        sys.exit("signups가 visits보다 많을 수 없습니다")
    fdt = {
        "visits": args.visits,
        "clicks": args.clicks,
        "signups": args.signups,
        "paid": args.paid,
        "url": args.url or (idea.get("fdt") or {}).get("url", ""),
        "updated_at": now(),
    }
    fdt["verdict"], fdt["message"] = judge_fdt(fdt, board["settings"])
    if idea.get("pay_pending"):
        # 가치 기반으로 지불 관문을 통과한 아이디어는 결제 의사(선결제)가 1건 이상 나와야 go
        if fdt["verdict"] == "go" and args.paid < 1:
            fdt["verdict"] = "retry"
            fdt["message"] += " · 💳 지불 검증 필요 아이디어라 선결제(또는 가격 확인 후 결제 예약) 1건 이상이 있어야 통과"
        elif args.paid >= 1:
            idea["pay_pending"]["proven"] = {"paid": args.paid, "at": now()}
            fdt["message"] += f" · 💳 결제 의사 {args.paid}건 확인 — 지불 검증 완료"
    idea["fdt"] = fdt
    idea["updated_at"] = now()
    save(path, board)
    print(f"{idea['id']} {idea['title']}: {fdt['verdict'].upper()} — {fdt['message']}")
    return 0


def cmd_due(args):
    board = load(board_path(args))
    today = dt.date.today().isoformat()
    due = [
        i for i in board["ideas"]
        if i["stage"] == "review" and (not i.get("next_review") or i["next_review"] <= today)
    ]
    for i in due:
        print(f"{i['id']}  {i['title']}  (리뷰 예정일 {i.get('next_review') or '미정'})")
    if not due:
        print("오늘 리뷰할 아이디어 없음")
    return 0


def cmd_set(args):
    path = board_path(args)
    board = load(path)
    for pair in args.pairs:
        key, _, value = pair.partition("=")
        if key not in DEFAULT_SETTINGS:
            sys.exit(f"unknown setting {key!r}. use: {', '.join(DEFAULT_SETTINGS)}")
        if key in NUMERIC_SETTINGS:
            num = float(value)
            board["settings"][key] = int(num) if num.is_integer() and isinstance(DEFAULT_SETTINGS[key], int) else num
        else:
            board["settings"][key] = value
    save(path, board)
    print(json.dumps(board["settings"], ensure_ascii=False))
    return 0


class Handler(BaseHTTPRequestHandler):
    board_file = None

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, payload):
        self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _board(self):
        board = read_board(self.board_file)
        board["stage_labels"] = STAGE_LABELS
        board["has_research"] = [
            i["id"] for i in board["ideas"] if research_path(self.board_file, i["id"]).exists()
        ]
        return board

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html", "/dashboard.html"):
                return self._send(200, (SCRIPT_DIR / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/board":
                return self._json(200, self._board())
            if path.startswith("/api/research/"):
                idea_id = path.rsplit("/", 1)[-1]
                rp = research_path(self.board_file, idea_id)
                if not ID_RE.match(idea_id) or not rp.exists():
                    return self._json(404, {"error": "no research"})
                return self._json(200, {"id": idea_id, "markdown": rp.read_text(encoding="utf-8")})
        except (BoardError, ValueError, OSError) as exc:
            return self._json(500, {"error": str(exc)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/board":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            board = json.loads(self.rfile.read(length))
            current = read_board(self.board_file)
            if int(board.get("rev", -1)) != int(current.get("rev", 0)):
                return self._json(409, {"error": "보드가 다른 곳(Claude/CLI)에서 바뀌었습니다. 새로 불러옵니다.",
                                        "board": self._board()})
            board.pop("stage_labels", None)
            board.pop("has_research", None)
            settings = {**DEFAULT_SETTINGS, **board.get("settings", {})}
            for idea in board.get("ideas", []):
                if idea.get("fdt") and idea["fdt"].get("visits"):
                    idea["fdt"]["verdict"], idea["fdt"]["message"] = judge_fdt(idea["fdt"], settings)
            save(self.board_file, board)
        except (ValueError, KeyError, TypeError, BoardError) as exc:
            return self._json(400, {"error": str(exc)})
        return self._json(200, self._board())


class LabServer(ThreadingHTTPServer):
    # Windows에서 SO_REUSEADDR는 이미 쓰는 포트를 조용히 같이 잡아버리므로 끈다
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def cmd_serve(args):
    path = board_path(args).resolve()
    if not path.exists():
        save(path, {"version": 1, "rev": 0, "settings": dict(DEFAULT_SETTINGS), "ideas": []})
    Handler.board_file = path
    try:
        server = LabServer(("127.0.0.1", args.port), Handler)
    except OSError:
        sys.exit(f"포트 {args.port}가 이미 사용 중입니다. 대시보드가 이미 떠 있으면 http://127.0.0.1:{args.port}/ 를 여세요. "
                 f"다른 포트: serve --port {args.port + 1}")
    url = f"http://127.0.0.1:{args.port}/"
    print(f"dashboard: {url}  (board: {path})  Ctrl+C to stop", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--board", default=os.path.join("lab", "board.json"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    p = sub.add_parser("add")
    p.add_argument("--title", required=True)
    p.add_argument("--p", help="P-Code: who has which problem")
    p.add_argument("--s", help="S-Code: solution and business model")
    p.add_argument("--notes")
    p.add_argument("--from", dest="parent", help="id of the idea this one pivots from")
    p.add_argument("--tags", help="comma-separated tags, e.g. B2B,자영업")
    p.add_argument("--market", choices=MARKETS, help="kr(한국) | global(해외) | both")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("timing", help="타이밍 대기·재검토 날짜가 온 아이디어")
    p.add_argument("--date", help="기준일 YYYY-MM-DD(기본 오늘)")
    p.add_argument("--all", action="store_true", help="날짜가 안 온 것까지 전부")
    p.set_defaults(func=cmd_timing)

    p = sub.add_parser("market", help="시장 표시 바꾸기: kr | global | both (대시보드 🌍 표시)")
    p.add_argument("id")
    p.add_argument("value", choices=MARKETS)
    p.set_defaults(func=cmd_market)

    p = sub.add_parser("list")
    p.add_argument("--stage", choices=STAGES)
    p.set_defaults(func=cmd_list)

    sub.add_parser("status").set_defaults(func=cmd_status)

    p = sub.add_parser("show")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("move")
    p.add_argument("id")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("--verdict", choices=VERDICTS)
    p.add_argument("--reason", required=True, help="why (evidence, one line)")
    p.add_argument("--priority", type=int)
    p.add_argument("--force", action="store_true", help="ignore the parallel limit / missing scores")
    p.add_argument("--why", choices=list(DROP_TYPES), help="Drop 사유 유형(생략하면 자동 분류)")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("score")
    p.add_argument("id")
    p.add_argument("pairs", nargs="+", metavar="key=value")
    p.add_argument("--prelim", action="store_true", help="provisional scores (e.g. easy/moat/scale before stage 5)")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("note")
    p.add_argument("id")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    p.set_defaults(func=cmd_note)

    p = sub.add_parser("edit")
    p.add_argument("id")
    p.add_argument("--title")
    p.add_argument("--p")
    p.add_argument("--s")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_edit)

    p = sub.add_parser("fdt")
    p.add_argument("id")
    p.add_argument("--visits", type=int, required=True)
    p.add_argument("--clicks", type=int, default=0)
    p.add_argument("--signups", type=int, required=True)
    p.add_argument("--paid", type=int, default=0)
    p.add_argument("--url")
    p.set_defaults(func=cmd_fdt)

    p = sub.add_parser("fdt-start")
    p.add_argument("id")
    p.add_argument("--url", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fdt_start)

    p = sub.add_parser("import")
    p.add_argument("file")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("stats")
    p.add_argument("--tags", action="store_true", help="saturation map by tag instead of by source")
    p.add_argument("--min", type=int, default=3, help="hide tags with fewer candidates")
    p.add_argument("--stages", action="store_true")
    p.set_defaults(func=cmd_stats)
    p = sub.add_parser("exceptions")
    p.add_argument("--md", action="store_true")
    p.set_defaults(func=cmd_exceptions)
    sub.add_parser("pending").set_defaults(func=cmd_pending)

    p = sub.add_parser("gated")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_gated)

    p = sub.add_parser("rank")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_rank)

    p = sub.add_parser("fdt-scaffold")
    p.add_argument("target", help="idea id or bundle name")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fdt_scaffold)

    p = sub.add_parser("bundle")
    p.add_argument("name", nargs="?")
    p.add_argument("ids", nargs="*")
    p.add_argument("--remove", action="store_true")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser("drops")
    p.add_argument("--type", choices=list(DROP_TYPES))
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--md", action="store_true")
    p.set_defaults(func=cmd_drops)

    p = sub.add_parser("gate")
    p.add_argument("id")
    p.add_argument("--set", nargs="*", help="key=pass|fail|unknown (compete pain pay math build redteam)")
    p.add_argument("--note")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("audit")
    p.add_argument("file")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("verify")
    p.add_argument("id")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ok", action="store_true")
    g.add_argument("--fail", action="store_true")
    p.add_argument("--note", required=True, help="what was opened and what it showed")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("apply")
    p.add_argument("file")
    p.set_defaults(func=cmd_apply)

    sub.add_parser("due").set_defaults(func=cmd_due)

    p = sub.add_parser("set")
    p.add_argument("pairs", nargs="+", metavar="key=value")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
