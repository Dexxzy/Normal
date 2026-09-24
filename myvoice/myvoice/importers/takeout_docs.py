"""Import Google Docs from a Google Takeout export.

How to get the export: takeout.google.com -> Deselect all -> tick Drive ->
"Multiple formats" -> set Documents to TXT (or Markdown) -> export.
Unzip, then:

    python -m myvoice.importers.takeout_docs ~/Downloads/Takeout

Handles .txt, .md, .html and .docx (docx parsed from its XML, no deps).
Skips spreadsheets, slides, PDFs and anything under a "Shared" folder unless
--include-shared is passed, since shared docs are often someone else's words.
"""

from __future__ import annotations

import argparse
import html
import re
import zipfile
from pathlib import Path

from ._common import looks_like_prose, write_sample

TEXT_EXTS = {".txt", ".md", ".markdown"}


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n\n", xml)
    xml = re.sub(r"<w:tab/>", " ", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(text)


def html_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<(script|style).*?</\1>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"</(p|div|h[1-6]|li|br)>", "\n\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(text)


def extract(path: Path) -> str | None:
    suf = path.suffix.lower()
    if suf in TEXT_EXTS:
        return path.read_text(encoding="utf-8", errors="replace")
    if suf == ".docx":
        return docx_text(path)
    if suf in {".html", ".htm"}:
        return html_text(path)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("takeout_dir")
    ap.add_argument("--out", default="samples/docs")
    ap.add_argument("--min-words", type=int, default=60)
    ap.add_argument("--include-shared", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.takeout_dir).expanduser()
    kept = skipped = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if not args.include_shared and any(p.lower().startswith("shared") for p in path.parts):
            continue
        text = extract(path)
        if text is None:
            continue
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text.split()) < args.min_words or not looks_like_prose(text, min_words=args.min_words):
            skipped += 1
            continue
        write_sample(args.out, path.stem, text)
        kept += 1
    print(f"kept {kept} docs, skipped {skipped} (too short / not prose) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
