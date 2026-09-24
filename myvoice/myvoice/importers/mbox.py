"""Import emails you sent from an .mbox (Gmail Takeout, Apple Mail export).

Gmail: takeout.google.com -> Mail -> "All mail data included" -> choose only
the Sent label. Then:

    python -m myvoice.importers.mbox ~/Downloads/Takeout/Mail/Sent.mbox --me you@gmail.com

Quoted replies ("On ... wrote:", "> " lines), forwarded headers and signatures
are stripped so only the part you typed remains.
"""

from __future__ import annotations

import argparse
import email
import mailbox
import re
from email.header import decode_header, make_header

from ._common import clean_message, looks_like_prose, write_sample

QUOTE_START = re.compile(r"^(On .{5,120}wrote:|-{2,}\s*Original Message\s*-{2,}|From: .+|Begin forwarded message:)\s*$", re.M | re.I)
SIG = re.compile(r"^--\s*$", re.M)


def body_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""


def strip_quotes(text: str) -> str:
    m = QUOTE_START.search(text)
    if m:
        text = text[: m.start()]
    m = SIG.search(text)
    if m:
        text = text[: m.start()]
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mbox_path")
    ap.add_argument("--me", required=True, help="your address; only messages From: it are kept")
    ap.add_argument("--out", default="samples/email")
    ap.add_argument("--min-words", type=int, default=30)
    args = ap.parse_args(argv)

    box = mailbox.mbox(args.mbox_path)
    kept = seen = 0
    for msg in box:
        seen += 1
        if args.me.lower() not in (msg.get("From") or "").lower():
            continue
        text = clean_message(strip_quotes(body_text(msg)))
        if len(text.split()) < args.min_words or not looks_like_prose(text, min_words=args.min_words):
            continue
        subject = str(make_header(decode_header(msg.get("Subject") or "no subject")))
        write_sample(args.out, subject, text)
        kept += 1
    print(f"{seen} messages scanned, {kept} written -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
