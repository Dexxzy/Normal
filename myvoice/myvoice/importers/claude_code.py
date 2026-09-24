"""Import your prompts from local Claude Code sessions (~/.claude/projects).

Each session is a .jsonl of events; user turns with plain string content are
your typed prompts. Tool results and pasted content are skipped.

    python -m myvoice.importers.claude_code
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._common import clean_message, looks_like_prose, write_sample


def user_prompts(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "user" or ev.get("isMeta"):
            continue
        content = (ev.get("message") or {}).get("content")
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            content = "\n".join(texts)
        if isinstance(content, str) and content.strip() and not content.startswith("<"):
            out.append(content)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="~/.claude/projects")
    ap.add_argument("--out", default="samples/claude_code")
    ap.add_argument("--min-words", type=int, default=12)
    ap.add_argument("--min-file-words", type=int, default=60)
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    files = words = 0
    for path in sorted(root.rglob("*.jsonl")):
        turns = [clean_message(t) for t in user_prompts(path) if looks_like_prose(t, min_words=args.min_words)]
        text = "\n\n".join(t for t in turns if len(t.split()) >= args.min_words)
        if len(text.split()) < args.min_file_words:
            continue
        write_sample(args.out, f"{path.parent.name}_{path.stem[:8]}", text)
        files += 1
        words += len(text.split())
    print(f"wrote {files} files, {words} words -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
