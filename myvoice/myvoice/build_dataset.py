"""Turn raw writing samples into (neutral -> yours) training pairs.

You only have one side of the pair: your text. Nobody has a "plain" version
of each thing you wrote. So we make it: Claude rewrites each chunk into flat,
standard, voice-less prose that keeps every fact. The model then learns the
direction *neutral -> you*, which is exactly the paraphrase task.

Output: data/pairs.jsonl, one {"id","source","neutral","original"} per line.
Re-running skips ids already present, so it is safe to interrupt.

    python -m myvoice.build_dataset --samples samples --variants 2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .corpus import Chunk, build_corpus
from .curate import load_decisions

NEUTRALIZE_SYSTEM = """You rewrite text into deliberately plain, neutral, standard English.

Rules:
- Preserve every fact, claim, opinion, and the order of ideas. Do not summarize, do not add, do not soften or strengthen anything.
- Remove all personal style: use standard capitalization and punctuation, expand contractions, replace slang and idioms with plain words, make sentence lengths ordinary, drop verbal tics and filler.
- Keep the same person (first person stays first person) and the same tense.
- Keep paragraph breaks where the original has them.
- Output only the rewritten text, nothing else."""

VARIANT_HINTS = [
    "",
    "Make this version slightly more formal and evenly paced than a typical neutral rewrite.",
    "Make this version terse and matter-of-fact, shorter sentences, no flourish.",
]


def load_pairs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default="data/pairs.jsonl")
    ap.add_argument("--curation", default="data/curation.jsonl", help="decisions from curate.py; missing file = keep all")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--variants", type=int, default=1, help="neutral rewrites per chunk (1-3); more = more training data")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="only process the first N chunks (for a dry run)")
    ap.add_argument("--min-words", type=int, default=40)
    ap.add_argument("--max-words", type=int, default=220)
    args = ap.parse_args(argv)

    chunks = build_corpus(args.samples, min_words=args.min_words, max_words=args.max_words)
    decisions = load_decisions(Path(args.curation))
    if decisions:
        before = len(chunks)
        chunks = [c for c in chunks if decisions.get(c.id, {"keep": True})["keep"]]
        print(f"curation: {len(chunks)}/{before} chunks kept")
    if args.limit:
        chunks = chunks[: args.limit]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {(p["id"], p.get("variant", 0)) for p in load_pairs(out)}
    variants = max(1, min(args.variants, len(VARIANT_HINTS)))
    jobs = [(c, v) for c in chunks for v in range(variants) if (c.id, v) not in done]
    print(f"{len(chunks)} chunks, {len(jobs)} rewrites to do ({len(done)} already present)")
    if not jobs:
        return 0

    from .llm import complete, get_client, run_parallel

    client = get_client()

    def neutralize(job: tuple[Chunk, int]) -> str:
        chunk, v = job
        hint = VARIANT_HINTS[v]
        user = (hint + "\n\n" if hint else "") + "Text to rewrite:\n\n" + chunk.text
        return complete(client, system=NEUTRALIZE_SYSTEM, user=user, model=args.model, effort="low", max_tokens=2048)

    failures = 0
    with out.open("a", encoding="utf-8") as f:
        for (chunk, v), neutral, err in run_parallel(jobs, neutralize, workers=args.workers, label="neutralizing"):
            if err or not neutral or not neutral.strip():
                failures += 1
                continue
            f.write(
                json.dumps(
                    {"id": chunk.id, "variant": v, "source": chunk.source, "neutral": neutral.strip(), "original": chunk.text},
                    ensure_ascii=False,
                )
                + "\n"
            )
            f.flush()
    total = len(load_pairs(out))
    print(f"wrote {out}: {total} pairs total, {failures} failures this run")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
