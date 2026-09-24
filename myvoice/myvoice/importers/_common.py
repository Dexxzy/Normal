from __future__ import annotations

import re
from pathlib import Path

FENCE = re.compile(r"```.*?```", re.S)
URL = re.compile(r"https?://\S+")


def safe_name(name: str, limit: int = 80) -> str:
    name = re.sub(r"[^\w.-]+", "_", name).strip("._")
    return (name[:limit] or "untitled")


def looks_like_prose(text: str, min_words: int = 8, max_symbol_ratio: float = 0.12) -> bool:
    """Reject snippets that are mostly code, logs, paths or pasted junk."""
    words = text.split()
    if len(words) < min_words:
        return False
    stripped = FENCE.sub("", text)
    stripped = URL.sub("", stripped)
    if not stripped.strip():
        return False
    symbols = sum(1 for ch in stripped if ch in "{}[]<>=|\\/$#@;`~^*_")
    if symbols / max(len(stripped), 1) > max_symbol_ratio:
        return False
    lines = [ln for ln in stripped.splitlines() if ln.strip()]
    # traceback / log shaped: lots of short lines with no sentence punctuation
    if len(lines) >= 6 and sum(1 for ln in lines if ln.rstrip()[-1:] in ".!?") < len(lines) / 4:
        return False
    return True


def clean_message(text: str) -> str:
    text = FENCE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def write_sample(out_dir: str | Path, name: str, text: str) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{safe_name(name)}.txt"
    i = 1
    while path.exists():
        path = out / f"{safe_name(name)}_{i}.txt"
        i += 1
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def group_bursts(items: list[tuple[float, str]], gap_seconds: float = 900) -> list[str]:
    """Merge (timestamp, text) messages sent within `gap_seconds` of each other
    into one paragraph, so a run of five quick texts reads as one thought."""
    items = sorted(items)
    groups: list[list[str]] = []
    last = None
    for ts, text in items:
        if last is None or ts - last > gap_seconds:
            groups.append([])
        groups[-1].append(text.strip())
        last = ts
    return [" ".join(g) for g in groups if g]
