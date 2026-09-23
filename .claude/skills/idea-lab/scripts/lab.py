#!/usr/bin/env python3
"""idea-lab board manager (standard library only).

The board lives in lab/board.json under the current folder. Claude and the
dashboard both read and write that one file.

  init                          create lab/board.json
  add --title T --p P --s S     add an idea at the ideation stage
  list [--stage S]              show ideas grouped by stage
  show ID                       print one idea as JSON
  move ID STAGE                 move an idea and log the decision
  score ID key=value ...        record review scores (1-5)
  fdt ID --visits N ...         record fake-door-test numbers and judge them
  due                           ideas in review whose 2-day review is due
  serve [--port 8765]           open the dashboard (reads/writes board.json)
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
VERDICTS = ["go", "drop", "hold", "retry"]
DEFAULT_SETTINGS = {
    "max_parallel": 10,
    "fdt_min_visits": 200,
    "fdt_go_rate": 0.05,
    "fdt_retry_rate": 0.02,
    "review_every_days": 2,
    "target_monthly_profit_krw": 3000000,
}
SCRIPT_DIR = Path(__file__).resolve().parent


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def board_path(args):
    return Path(args.board)


def load(path):
    if not path.exists():
        sys.exit(f"{path} not found. Run: lab.py init")
    board = json.loads(path.read_text(encoding="utf-8"))
    board.setdefault("settings", {})
    for key, value in DEFAULT_SETTINGS.items():
        board["settings"].setdefault(key, value)
    board.setdefault("ideas", [])
    return board


def save(path, board):
    """Write atomically so the dashboard and CLI never see a half-written file."""
    validate(board)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".board-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def validate(board):
    if not isinstance(board.get("ideas"), list):
        raise ValueError("board.ideas must be a list")
    ids = set()
    for idea in board["ideas"]:
        if idea.get("stage") not in STAGES:
            raise ValueError(f"idea {idea.get('id')}: unknown stage {idea.get('stage')!r}")
        if not idea.get("id") or idea["id"] in ids:
            raise ValueError(f"missing or duplicate idea id {idea.get('id')!r}")
        ids.add(idea["id"])


def find(board, idea_id):
    for idea in board["ideas"]:
        if idea["id"] == idea_id:
            return idea
    sys.exit(f"no idea with id {idea_id}")


def next_id(board):
    nums = [int(i["id"][1:]) for i in board["ideas"] if i["id"][1:].isdigit()]
    return f"i{max(nums, default=0) + 1:03d}"


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


def cmd_init(args):
    path = board_path(args)
    if path.exists():
        print(f"{path} already exists")
        return 0
    save(path, {"version": 1, "settings": dict(DEFAULT_SETTINGS), "ideas": []})
    print(f"created {path}")
    return 0


def cmd_add(args):
    path = board_path(args)
    board = load(path)
    idea = {
        "id": next_id(board),
        "title": args.title,
        "p_code": args.p or "",
        "s_code": args.s or "",
        "stage": "ideation",
        "priority": None,
        "scores": {},
        "fdt": None,
        "notes": args.notes or "",
        "log": [],
        "created_at": now(),
        "updated_at": now(),
        "next_review": None,
    }
    board["ideas"].append(idea)
    save(path, board)
    print(f"added {idea['id']}  {idea['title']}")
    return 0


def cmd_list(args):
    board = load(board_path(args))
    stages = [args.stage] if args.stage else STAGES
    for stage in stages:
        ideas = [i for i in board["ideas"] if i["stage"] == stage]
        if not ideas:
            continue
        ideas.sort(key=lambda i: (i.get("priority") is None, i.get("priority") or 0))
        print(f"\n## {STAGE_LABELS[stage]} ({len(ideas)})")
        for i in ideas:
            pri = f"P{i['priority']}" if i.get("priority") else "  -"
            extra = f"  FDT:{i['fdt']['verdict']}" if i.get("fdt") else ""
            print(f"  {i['id']}  {pri:>4}  {i['title']}{extra}")
    active = sum(1 for i in board["ideas"] if i["stage"] in ("filtering", "review"))
    print(f"\n병렬 실험 중: {active}/{board['settings']['max_parallel']}")
    return 0


def cmd_show(args):
    board = load(board_path(args))
    print(json.dumps(find(board, args.id), ensure_ascii=False, indent=2))
    return 0


def cmd_move(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    if args.stage in ("filtering", "review") and idea["stage"] not in ("filtering", "review"):
        active = sum(1 for i in board["ideas"] if i["stage"] in ("filtering", "review"))
        if active >= board["settings"]["max_parallel"] and not args.force:
            sys.exit(f"병렬 실험이 이미 {active}개입니다(최대 {board['settings']['max_parallel']}). --force로 무시")
    from_stage = idea["stage"]
    idea["stage"] = args.stage
    if args.priority is not None:
        idea["priority"] = args.priority
    if args.stage == "review":
        days = board["settings"]["review_every_days"]
        idea["next_review"] = (dt.date.today() + dt.timedelta(days=days)).isoformat()
    elif args.stage in ("done", "dropped"):
        idea["next_review"] = None
    log(idea, from_stage, args.stage, args.verdict, args.reason or "")
    save(path, board)
    print(f"{idea['id']}: {STAGE_LABELS[from_stage]} → {STAGE_LABELS[args.stage]}")
    return 0


def cmd_score(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    for pair in args.pairs:
        key, _, value = pair.partition("=")
        if not value:
            sys.exit(f"expected key=value, got {pair!r}")
        score = float(value)
        if not 1 <= score <= 5:
            sys.exit(f"{key}: score must be 1-5")
        idea.setdefault("scores", {})[key] = score
    idea["updated_at"] = now()
    save(path, board)
    print(json.dumps(idea["scores"], ensure_ascii=False))
    return 0


def cmd_fdt(args):
    path = board_path(args)
    board = load(path)
    idea = find(board, args.id)
    if args.visits <= 0:
        sys.exit("visits must be > 0")
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


class Handler(SimpleHTTPRequestHandler):
    board_file = None

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SCRIPT_DIR), **kw)

    def log_message(self, fmt, *args):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/dashboard.html"
        if self.path == "/api/board":
            board = load(self.board_file)
            board["stage_labels"] = STAGE_LABELS
            return self._json(200, board)
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/board":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            board = json.loads(self.rfile.read(length))
            board.pop("stage_labels", None)
            for idea in board.get("ideas", []):
                if idea.get("fdt") and idea["fdt"].get("visits"):
                    idea["fdt"]["verdict"], idea["fdt"]["message"] = judge_fdt(
                        idea["fdt"], {**DEFAULT_SETTINGS, **board.get("settings", {})}
                    )
            save(self.board_file, board)
        except (ValueError, KeyError, TypeError) as exc:
            return self._json(400, {"error": str(exc)})
        board["stage_labels"] = STAGE_LABELS
        return self._json(200, board)


def cmd_serve(args):
    path = board_path(args).resolve()
    if not path.exists():
        save(path, {"version": 1, "settings": dict(DEFAULT_SETTINGS), "ideas": []})
    Handler.board_file = path
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"dashboard: {url}  (board: {path})  Ctrl+C to stop")
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
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--stage", choices=STAGES)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("move")
    p.add_argument("id")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("--verdict", choices=VERDICTS)
    p.add_argument("--reason")
    p.add_argument("--priority", type=int)
    p.add_argument("--force", action="store_true", help="ignore the parallel experiment limit")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("score")
    p.add_argument("id")
    p.add_argument("pairs", nargs="+", metavar="key=value")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("fdt")
    p.add_argument("id")
    p.add_argument("--visits", type=int, required=True)
    p.add_argument("--clicks", type=int, default=0)
    p.add_argument("--signups", type=int, required=True)
    p.add_argument("--paid", type=int, default=0)
    p.add_argument("--url")
    p.set_defaults(func=cmd_fdt)

    sub.add_parser("due").set_defaults(func=cmd_due)

    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
