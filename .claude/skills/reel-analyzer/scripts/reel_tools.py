#!/usr/bin/env python3
"""reel-analyzer helper.

Subcommands:
  urls FILE                 classify media URLs collected from the reel page
  download URL OUT          download a CDN media file (range params stripped)
  probe FILE                list audio/video streams and duration
  frames VIDEO OUTDIR       save evenly spaced frames as PNG
  transcribe MEDIA OUTDIR   speech-to-text with faster-whisper
"""
import argparse
import base64
import json
import os
import sys
import urllib.parse
from pathlib import Path

RANGE_PARAMS = {"bytestart", "byteend"}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def full_track_url(url):
    """Drop the byte-range params Instagram adds so the whole track downloads."""
    parts = urllib.parse.urlsplit(url)
    query = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if k not in RANGE_PARAMS
    ]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def track_kind(url):
    """Guess progressive/audio/video from the base64 JSON in the `efg` param."""
    efg = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("efg")
    if not efg:
        return "unknown"
    try:
        data = json.loads(base64.urlsafe_b64decode(efg + "=" * (-len(efg) % 4)))
    except ValueError:
        return "unknown"
    tag = str(data.get("vencode_tag", "")).lower()
    if "progressive" in tag:
        return "progressive"
    if "audio" in tag:
        return "audio"
    return "video" if tag else "unknown"


def cmd_urls(args):
    text = Path(args.file).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
        lines = raw if isinstance(raw, list) else [raw]
    except json.JSONDecodeError:
        lines = text.splitlines()

    seen = {}
    for line in lines:
        line = str(line).strip()
        if line.startswith("http"):
            url = full_track_url(line)
            seen.setdefault(url, track_kind(url))

    order = {"progressive": 0, "audio": 1, "video": 2, "unknown": 3}
    ranked = sorted(seen.items(), key=lambda kv: order[kv[1]])
    for url, kind in ranked:
        print(f"{kind}\t{url}")
    if not ranked:
        print("no media urls found", file=sys.stderr)
        return 1
    return 0


def cmd_download(args):
    import requests

    url = full_track_url(args.url)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Referer": "https://www.instagram.com/"}
    with requests.get(url, headers=headers, stream=True, timeout=60) as resp:
        if resp.status_code != 200:
            print(f"download failed: HTTP {resp.status_code} (URL may have expired; reload the reel page and collect URLs again)", file=sys.stderr)
            return 1
        with out.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    size = out.stat().st_size
    if size == 0:
        print("download failed: empty file", file=sys.stderr)
        return 1
    print(f"saved {out} ({size / 1024:.0f} KB)")
    return 0


def probe(path):
    import av

    with av.open(str(path)) as container:
        streams = [
            {"index": s.index, "type": s.type, "codec": s.codec_context.name}
            for s in container.streams
            if s.type in ("audio", "video")
        ]
        duration = container.duration / av.time_base if container.duration else None
    return {"streams": streams, "duration_sec": duration}


def cmd_probe(args):
    print(json.dumps(probe(args.file), ensure_ascii=False, indent=2))
    return 0


def cmd_frames(args):
    import av

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with av.open(str(args.video)) as container:
        if not container.streams.video:
            print("no video stream in file", file=sys.stderr)
            return 1
        stream = container.streams.video[0]
        duration = container.duration / av.time_base if container.duration else 0
        every = max(args.every, duration / args.max) if duration else args.every

        saved = []
        next_t = 0.0
        for frame in container.decode(stream):
            if frame.time is None or frame.time < next_t:
                continue
            path = outdir / f"frame_{frame.time:06.1f}s.png"
            frame.to_image().save(path)
            saved.append(path.name)
            next_t = frame.time + every
            if len(saved) >= args.max:
                break
    print(f"saved {len(saved)} frames to {outdir} (every {every:.1f}s)")
    return 0


def fmt_ts(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def cmd_transcribe(args):
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from faster_whisper import WhisperModel

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    language = None if args.lang == "auto" else args.lang

    print(f"loading model {args.model} (first run downloads it)...", flush=True)
    try:
        model = WhisperModel(args.model, device="cpu", compute_type="int8")
    except Exception as exc:  # network or memory problems surface here
        print(
            f"model load failed: {exc}\n"
            "network error -> check access to huggingface.co; out of memory -> retry with --model small",
            file=sys.stderr,
        )
        return 1

    segments, info = model.transcribe(str(args.media), language=language, vad_filter=True)
    rows = [
        {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
        for seg in segments
    ]

    lines = [f"[{fmt_ts(r['start'])}] {r['text']}" for r in rows]
    (outdir / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (outdir / "transcript.json").write_text(
        json.dumps(
            {"language": info.language, "duration_sec": info.duration, "segments": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"language={info.language} duration={info.duration:.1f}s segments={len(rows)}")
    print(f"saved {outdir / 'transcript.txt'}")
    if not rows:
        print("warning: no speech detected (music-only reel?)", file=sys.stderr)
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("urls", help="classify media URLs (one per line or JSON array)")
    p.add_argument("file")
    p.set_defaults(func=cmd_urls)

    p = sub.add_parser("download", help="download a media URL")
    p.add_argument("url")
    p.add_argument("out")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("probe", help="show streams and duration")
    p.add_argument("file")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("frames", help="extract evenly spaced frames")
    p.add_argument("video")
    p.add_argument("outdir")
    p.add_argument("--every", type=float, default=2.0, help="minimum seconds between frames")
    p.add_argument("--max", type=int, default=15, help="maximum number of frames")
    p.set_defaults(func=cmd_frames)

    p = sub.add_parser("transcribe", help="speech-to-text")
    p.add_argument("media")
    p.add_argument("outdir")
    p.add_argument("--model", default="large-v3-turbo", help="faster-whisper model name (small is faster, less accurate)")
    p.add_argument("--lang", default="ko", help="language code, or 'auto'")
    p.set_defaults(func=cmd_transcribe)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
