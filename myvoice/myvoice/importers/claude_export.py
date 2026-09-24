"""Import your side of claude.ai conversations.

Get the export: claude.ai -> Settings -> Privacy -> Export data. You get an
email with a zip containing conversations.json. Then:

    python -m myvoice.importers.claude_export ~/Downloads/data-2026-09-24/conversations.json

Only "human" turns are kept. Turns that are mostly pasted code, logs, or
error output are dropped, and fenced code blocks are stripped from the rest.
One file per conversation goes to samples/claude/.

Note: how you talk to an assistant is a distinct register (lots of imperatives,
half-sentences). It's still you, but profile it separately from docs or
messages before mixing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._common import clean_message, looks_like_prose, write_sample


def human_turns(convo: dict) -> list[str]:
    out = []
    for m in convo.get("chat_messages", []):
        if m.get("sender") != "human":
            continue
        text = m.get("text") or ""
        if not text and isinstance(m.get("content"), list):
            text = "\n".join(c.get("text", "") for c in m["content"] if c.get("type") == "text")
        if text.strip():
            out.append(text)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("conversations_json")
    ap.add_argument("--out", default="samples/claude")
    ap.add_argument("--min-words", type=int, default=12, help="drop shorter turns")
    ap.add_argument("--min-file-words", type=int, default=60)
    args = ap.parse_args(argv)

    data = json.loads(Path(args.conversations_json).expanduser().read_text(encoding="utf-8"))
    files = words = 0
    for convo in data:
        turns = [clean_message(t) for t in human_turns(convo) if looks_like_prose(t, min_words=args.min_words)]
        turns = [t for t in turns if len(t.split()) >= args.min_words]
        text = "\n\n".join(turns)
        if len(text.split()) < args.min_file_words:
            continue
        name = convo.get("name") or convo.get("uuid") or "conversation"
        write_sample(args.out, name, text)
        files += 1
        words += len(text.split())
    print(f"{len(data)} conversations; wrote {files} files, {words} words -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
