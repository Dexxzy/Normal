"""Load writing samples and split them into training-sized chunks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path

SAMPLE_EXTS = {".txt", ".md", ".markdown"}
SKIP_NAMES = {"readme.md", "readme.txt"}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=\S)")


@dataclass
class Chunk:
    id: str
    source: str
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> dict:
        return asdict(self)


def load_samples(sample_dir: str | Path) -> list[tuple[str, str]]:
    """Return [(relative_path, text)] for every sample file, sorted by path."""
    root = Path(sample_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"sample directory not found: {root}")
    out: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SAMPLE_EXTS:
            continue
        if path.name.lower() in SKIP_NAMES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.strip():
            out.append((str(path.relative_to(root)), text))
    return out


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def paragraphs(text: str) -> list[str]:
    """Split on blank lines, collapsing internal whitespace but keeping line intent."""
    paras = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    cleaned = []
    for p in paras:
        p = re.sub(r"[ \t]+", " ", p).strip()
        p = re.sub(r" ?\n ?", " ", p)  # soft-wrapped lines -> one paragraph
        if p:
            cleaned.append(p)
    return cleaned


def chunk_text(text: str, min_words: int = 40, max_words: int = 220) -> list[str]:
    """Group paragraphs into chunks of roughly min..max words.

    Short paragraphs get merged with their neighbours; oversized paragraphs are
    split at sentence boundaries. Chunks under ``min_words`` at the very end are
    kept only if nothing else exists (so tiny samples still produce output).
    """
    pieces: list[str] = []
    for p in paragraphs(text):
        if len(p.split()) <= max_words:
            pieces.append(p)
            continue
        buf: list[str] = []
        count = 0
        for s in split_sentences(p):
            n = len(s.split())
            if buf and count + n > max_words:
                pieces.append(" ".join(buf))
                buf, count = [], 0
            buf.append(s)
            count += n
        if buf:
            pieces.append(" ".join(buf))

    chunks: list[str] = []
    buf = []
    count = 0
    for p in pieces:
        n = len(p.split())
        if buf and count + n > max_words:
            chunks.append("\n\n".join(buf))
            buf, count = [], 0
        buf.append(p)
        count += n
        if count >= min_words:
            chunks.append("\n\n".join(buf))
            buf, count = [], 0
    if buf:
        tail = "\n\n".join(buf)
        if chunks and count < min_words:
            chunks[-1] = chunks[-1] + "\n\n" + tail
        else:
            chunks.append(tail)
    return chunks


def chunk_id(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}\0{text}".encode("utf-8")).hexdigest()[:12]


def build_corpus(sample_dir: str | Path, min_words: int = 40, max_words: int = 220) -> list[Chunk]:
    chunks: list[Chunk] = []
    for source, text in load_samples(sample_dir):
        for piece in chunk_text(text, min_words=min_words, max_words=max_words):
            chunks.append(Chunk(id=chunk_id(source, piece), source=source, text=piece))
    return chunks


def corpus_stats(chunks: list[Chunk]) -> dict:
    words = [c.words for c in chunks]
    return {
        "files": len({c.source for c in chunks}),
        "chunks": len(chunks),
        "total_words": sum(words),
        "avg_chunk_words": round(sum(words) / len(words), 1) if words else 0,
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Inspect the sample corpus.")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--show", type=int, default=2, help="print N example chunks")
    args = ap.parse_args()
    corpus = build_corpus(args.samples)
    print(json.dumps(corpus_stats(corpus), indent=2))
    for c in corpus[: args.show]:
        print(f"\n--- {c.source} [{c.id}] ({c.words} words)\n{c.text}")
