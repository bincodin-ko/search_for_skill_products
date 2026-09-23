#!/usr/bin/env python3
"""idea-lab board manager (standard library only).

The board lives in lab/board.json under the current folder. Claude and the
dashboard both read and write that one file. Research notes live next to it
in lab/ideas/<id>.md.

  init                          create lab/board.json
  add --title T --p P --s S     add an idea at the ideation stage (--from ID for a pivot)
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
import json
import os
import re
import socket
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STAGES = ["ideation", "incubating", "brainstorming", "filtering", "review", "done", "dropped"]
STAGE_LABELS = {
    "ideation": "1. Ideation",
    "incubating": "2. Incubating",
    "brainstorming": "3. Brainstorming",
    "filtering": "4. Filtering (FDT)",
    "review": "5. 2일마다 리뷰",
    "done": "DONE",
    "dropped": "Drop",
}
SHORT_LABELS = {
    "ideation": "Ideation", "incubating": "Incubating", "brainstorming": "Brainstorming",
    "filtering": "Filtering", "review": "리뷰", "done": "DONE", "dropped": "Drop",
}
ACTIVE = ("filtering", "review")
VERDICTS = ["go", "drop", "hold", "retry"]
SCORE_KEYS = ["need", "revenue", "tenx", "dist", "fit", "easy", "moat", "scale"]
# need/revenue <= 2 -> auto drop. dist = 첫 고객에게 닿는 길, fit = 창업자 적합도(settings.founder 기준)
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


def save(path, board):
    """Write atomically and bump rev so a stale dashboard can't overwrite newer changes."""
    validate(board)
    board["rev"] = int(board.get("rev", 0)) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".board-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


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
    flow = " → ".join(f"{SHORT_LABELS[st]} {n[st]}" for st in STAGES[:6])
    return f"{flow} · Drop {n['dropped']} · 병렬 {count_active(board)}/{board['settings']['max_parallel']}"


def cmd_init(args):
    path = board_path(args)
    if path.exists():
        print(f"{path} already exists")
        return 0
    save(path, {"version": 1, "rev": 0, "settings": dict(DEFAULT_SETTINGS), "ideas": []})
    (path.parent / "ideas").mkdir(exist_ok=True)
    print(f"created {path}")
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
        if active >= board["settings"]["max_parallel"] and not args.force:
            sys.exit(f"병렬 실험이 이미 {active}개입니다(최대 {board['settings']['max_parallel']}). --force로 무시")
    if args.stage == "filtering" and idea["stage"] != "filtering":
        missing = [k for k in ("need", "revenue") if k not in idea.get("scores", {})]
        if missing and not args.force:
            sys.exit(f"3단계 점수({', '.join(missing)})가 없습니다. LAB score 먼저, 또는 --force")
    from_stage = idea["stage"]
    idea["stage"] = args.stage
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
    if not args.prelim and (s.get("need", 5) <= 2 or s.get("revenue", 5) <= 2):
        print("⚠ need 또는 revenue ≤ 2 → 3단계 자동 Drop 대상")
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


def cmd_edit(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    changes = {k: v for k, v in (("title", args.title), ("p_code", args.p), ("s_code", args.s)) if v}
    if not changes:
        sys.exit("바꿀 항목(--title/--p/--s)이 없습니다")
    idea.update(changes)
    log(idea, idea["stage"], idea["stage"], None, f"{', '.join(changes)} 수정: {args.reason}")
    save(path, board)
    print(f"{idea['id']}: {', '.join(changes)} 수정")
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


def cmd_apply(args):
    """Apply a researcher batch result: [{id, need, revenue, tenx, dist?, fit?, easy, moat, scale,
    verdict, reason, pivot?, note?, login_needed?}]. Only ideas still in brainstorming are touched."""
    path = board_path(args)
    board = load(path)
    rows = json.loads(Path(args.file).read_text(encoding="utf-8"))
    applied = dropped = 0
    for r in rows:
        idea = next((i for i in board["ideas"] if i["id"] == r.get("id")), None)
        if not idea or idea["stage"] != "brainstorming":
            continue
        idea.setdefault("scores", {}).update(
            {k: clamp_score(r[k]) for k in ("need", "revenue", "tenx", "dist", "fit") if r.get(k) is not None})
        idea.setdefault("prelim", {}).update(
            {k: clamp_score(r[k]) for k in ("easy", "moat", "scale") if r.get(k) is not None})
        note = [f"[3단계 조사 {dt.date.today().isoformat()}] 상세: lab/ideas/{idea['id']}.md", str(r.get("note", "")).strip()]
        if r.get("pivot"):
            note.append(f"피벗안: {r['pivot']}")
        if r.get("login_needed"):
            note.append("로그인 필요 출처: " + ", ".join(map(str, r["login_needed"])))
        idea["notes"] = "\n".join(x for x in note if x)
        idea["research_verdict"] = r.get("verdict", "")
        idea["updated_at"] = now()
        applied += 1
        sc = idea["scores"]
        if sc.get("need", 5) <= 2 or sc.get("revenue", 5) <= 2:
            reason = f"조사: {r.get('reason', '')}"
            if r.get("pivot"):
                reason += f" · 피벗안: {r['pivot']}"
            if r.get("verdict") in ("pass", "pivot"):
                reason += " · ⚑ 규칙 예외 후보(조사원은 " + r["verdict"] + ")"
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
    p.set_defaults(func=cmd_add)

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
