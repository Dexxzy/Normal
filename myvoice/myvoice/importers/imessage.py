"""Import your own sent iMessages from a Mac.

Messages live in ~/Library/Messages/chat.db (SQLite). Your terminal app needs
Full Disk Access (System Settings -> Privacy & Security -> Full Disk Access)
or the read fails with "unable to open database file". Nothing is modified;
the DB is opened read-only.

    python -m myvoice.importers.imessage
    python -m myvoice.importers.imessage --db ~/Desktop/chat.db --min-words 6

Only messages with is_from_me = 1 are read. Bursts of texts sent within
--gap seconds of each other are merged into one paragraph, and one file per
conversation is written to samples/imessage/. Recent macOS stores text in a
binary attributedBody column; a best-effort decoder handles that.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from ._common import clean_message, group_bursts, looks_like_prose, write_sample

APPLE_EPOCH = 978307200  # 2001-01-01 in unix seconds

SQL = """
SELECT m.ROWID, m.date, m.text, m.attributedBody, c.chat_identifier
FROM message m
LEFT JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
LEFT JOIN chat c ON c.ROWID = cmj.chat_id
WHERE m.is_from_me = 1
"""


def decode_attributed_body(blob: bytes | None) -> str | None:
    """Pull the NSString payload out of Apple's typedstream blob."""
    if not blob:
        return None
    idx = blob.find(b"NSString")
    if idx == -1:
        return None
    rest = blob[idx + len(b"NSString") :]
    # skip class-info bytes, then a "+" marks the start of the length-prefixed string
    plus = rest.find(b"+")
    if plus == -1:
        return None
    rest = rest[plus + 1 :]
    if not rest:
        return None
    length = rest[0]
    start = 1
    if length == 0x81:  # 2-byte little-endian length follows
        length = int.from_bytes(rest[1:3], "little")
        start = 3
    return rest[start : start + length].decode("utf-8", errors="replace")


def to_unix(date: int | float) -> float:
    if date > 1e12:  # nanoseconds since 2001
        date = date / 1e9
    return date + APPLE_EPOCH


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="~/Library/Messages/chat.db")
    ap.add_argument("--out", default="samples/imessage")
    ap.add_argument("--min-words", type=int, default=5, help="ignore shorter merged bursts")
    ap.add_argument("--gap", type=int, default=900, help="seconds between texts to still merge them")
    ap.add_argument("--min-file-words", type=int, default=60, help="skip conversations with less than this")
    args = ap.parse_args(argv)

    db = Path(args.db).expanduser()
    if not db.exists():
        raise SystemExit(f"not found: {db}")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    per_chat: dict[str, list[tuple[float, str]]] = defaultdict(list)
    rows = 0
    for _rowid, date, text, body, chat in conn.execute(SQL):
        rows += 1
        msg = text or decode_attributed_body(body)
        if not msg or not msg.strip():
            continue
        msg = re.sub(r"￼", "", msg).strip()  # attachment placeholder
        if not msg:
            continue
        per_chat[chat or "unknown"].append((to_unix(date), msg))
    conn.close()

    files = 0
    total_words = 0
    for chat, items in per_chat.items():
        paras = [p for p in group_bursts(items, gap_seconds=args.gap) if len(p.split()) >= args.min_words]
        paras = [clean_message(p) for p in paras if looks_like_prose(p, min_words=args.min_words, max_symbol_ratio=0.2)]
        text = "\n\n".join(paras)
        if len(text.split()) < args.min_file_words:
            continue
        write_sample(args.out, chat, text)
        files += 1
        total_words += len(text.split())
    print(f"read {rows} sent messages across {len(per_chat)} chats; wrote {files} files, {total_words} words -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
