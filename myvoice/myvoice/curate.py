"""Decide which chunks are actually *your* writing.

Google Docs (and any long-lived document) tend to mix your prose with things
you didn't write: assignment instructions, pasted quotes, templates, rubrics,
meeting notes someone else typed, AI drafts. Training on those dilutes the
voice. This step labels every chunk keep/drop in two passes:

1. Heuristics (free, offline): numbered instruction lists, rubric/assignment
   vocabulary, quoted blocks, template placeholders, boilerplate.
2. Claude judge (optional, --llm): shown a handful of *trusted* chunks that
   are definitely you (from samples/imessage, samples/claude, or whatever you
   pass as --trusted) and asked whether each candidate chunk reads like the
   same author writing freely, or like instructions / someone else / a paste.

Outputs data/curation.jsonl (one decision per chunk id) and a human-readable
data/curation_review.md. build_dataset.py honours the decisions. To override
a call, edit the "keep" field in curation.jsonl; re-running keeps your edits
unless you pass --fresh.

    python -m myvoice.curate --samples samples/docs --trusted samples/imessage samples/claude --llm
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from .corpus import Chunk, build_corpus

INSTRUCTION_WORDS = re.compile(
    r"\b(instructions?|assignment|rubric|due date|due:|submit|prompt:|requirements?:|"
    r"objectives?:|learning outcomes?|grading|points possible|word count:|"
    r"please (?:read|complete|answer|submit)|you (?:will|must|should) (?:write|submit|include)|"
    r"terms (?:and|&) conditions|all rights reserved|confidential)\b",
    re.I,
)
PLACEHOLDER = re.compile(r"\[(?:insert|your|name|date|todo)[^\]]*\]|\{\{.*?\}\}|_{4,}", re.I)
QUOTED_LINE = re.compile(r"^\s*(>|“|\")", re.M)
NUMBERED = re.compile(r"^\s*(\d+[.)]|[a-z][.)]|[-*•])\s+\S", re.M)
IMPERATIVE_START = re.compile(
    r"^\s*(?:\d+[.)]|[-*•])?\s*(write|describe|explain|list|identify|discuss|compare|analy[sz]e|"
    r"read|complete|answer|include|use|create|choose|select|submit|make sure|ensure|do not|don't)\b",
    re.I | re.M,
)

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string", "enum": ["author", "instructions", "other_person", "pasted", "template", "unsure"]},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "label", "confidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """You are curating a corpus of one person's own writing for a style model.

You will see TRUSTED samples that are definitely written by the author, in their natural voice.
Then you will see CANDIDATE chunks pulled from that author's documents. Documents are messy:
they contain assignment prompts, rubrics, teacher/employer instructions, quotes, pasted articles,
templates, notes typed by other people, and AI-generated drafts, mixed in with the author's own prose.

For each candidate, decide:
- "author": the author's own free writing (essay body, journal, notes to self, message drafts). Rough spelling, lowercase, slang, and typos are NOT reasons to reject; those are often the strongest signals it is really them.
- "instructions": task prompts, rubrics, requirements, directions addressed to a reader.
- "other_person": clearly someone else speaking (teacher comments, colleague's notes, a quoted email).
- "pasted": published or reference text (article, lyrics, documentation, legal boilerplate) or polished AI-sounding prose that does not match the trusted samples.
- "template": placeholders, headers-only skeletons, forms.
- "unsure": genuinely ambiguous.

Judge by who is speaking and why the text exists, not by topic. Confidence is 0 to 1. Keep reasons under 15 words."""


def heuristic_flags(text: str) -> list[str]:
    flags = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    n_lines = max(len(lines), 1)
    if INSTRUCTION_WORDS.search(text):
        flags.append("instruction-vocab")
    if PLACEHOLDER.search(text):
        flags.append("placeholders")
    if len(QUOTED_LINE.findall(text)) / n_lines > 0.5:
        flags.append("quoted")
    numbered = len(NUMBERED.findall(text))
    imperative = len(IMPERATIVE_START.findall(text))
    if numbered >= 3 and imperative >= 2:
        flags.append("imperative-list")
    words = text.split()
    if words:
        title_case = sum(1 for w in words if w[:1].isupper()) / len(words)
        if title_case > 0.5 and len(words) > 20:
            flags.append("title-case-heavy")
    return flags


def heuristic_keep(flags: list[str]) -> bool:
    hard = {"placeholders", "quoted", "imperative-list", "title-case-heavy"}
    return not (hard & set(flags))


def load_decisions(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["id"]] = d
    return out


def llm_judge(client, model: str, trusted: list[Chunk], candidates: list[Chunk], batch: int = 8, workers: int = 4) -> dict[str, dict]:
    from .llm import complete_json, run_parallel

    trusted_text = "\n\n".join(f"<trusted>\n{c.text}\n</trusted>" for c in trusted)
    system = JUDGE_SYSTEM + "\n\nTRUSTED SAMPLES (definitely the author):\n\n" + trusted_text

    batches = [candidates[i : i + batch] for i in range(0, len(candidates), batch)]

    def judge(group: list[Chunk]) -> dict:
        user = "CANDIDATES:\n\n" + "\n\n".join(f'<candidate id="{c.id}">\n{c.text}\n</candidate>' for c in group)
        return complete_json(client, system=system, user=user, model=model, json_schema=JUDGE_SCHEMA, effort="low", max_tokens=4096)

    verdicts: dict[str, dict] = {}
    for group, result, err in run_parallel(batches, judge, workers=workers, label="judging batches"):
        if err:
            print(f"\nbatch failed ({err}); its {len(group)} chunks marked unsure")
            for c in group:
                verdicts[c.id] = {"label": "unsure", "confidence": 0.0, "reason": f"judge error: {err}"}
            continue
        for v in result["verdicts"]:
            verdicts[v["id"]] = v
    return verdicts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", default="samples/docs", help="chunks to curate")
    ap.add_argument("--trusted", nargs="*", default=[], help="dirs of writing that is definitely you")
    ap.add_argument("--out", default="data/curation.jsonl")
    ap.add_argument("--review", default="data/curation_review.md")
    ap.add_argument("--llm", action="store_true", help="also ask Claude to judge")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--n-trusted", type=int, default=6)
    ap.add_argument("--min-confidence", type=float, default=0.6, help="'author' below this becomes unsure")
    ap.add_argument("--keep-unsure", action="store_true", help="treat unsure as keep instead of drop")
    ap.add_argument("--fresh", action="store_true", help="ignore existing decisions / manual edits")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    chunks = build_corpus(args.samples)
    if not chunks:
        raise SystemExit(f"no chunks under {args.samples}")
    out_path = Path(args.out)
    prior = {} if args.fresh else load_decisions(out_path)

    decisions: dict[str, dict] = {}
    todo: list[Chunk] = []
    for c in chunks:
        if c.id in prior:
            decisions[c.id] = prior[c.id]
            continue
        flags = heuristic_flags(c.text)
        decisions[c.id] = {
            "id": c.id,
            "source": c.source,
            "words": c.words,
            "flags": flags,
            "label": "author" if heuristic_keep(flags) else "flagged",
            "confidence": None,
            "reason": "heuristics",
            "keep": heuristic_keep(flags),
            "manual": False,
        }
        if heuristic_keep(flags):
            todo.append(c)

    if args.llm and todo:
        trusted: list[Chunk] = []
        for d in args.trusted:
            trusted.extend(build_corpus(d))
        if not trusted:
            print("warning: no --trusted samples; the judge only has generic cues to go on")
        random.seed(0)
        sample = random.sample(trusted, min(args.n_trusted, len(trusted))) if trusted else []
        from .llm import get_client

        verdicts = llm_judge(get_client(), args.model, sample, todo, workers=args.workers)
        for c in todo:
            v = verdicts.get(c.id)
            if not v:
                continue
            d = decisions[c.id]
            label = v["label"]
            if label == "author" and v["confidence"] < args.min_confidence:
                label = "unsure"
            d.update(label=label, confidence=v["confidence"], reason=v["reason"])
            d["keep"] = label == "author" or (label == "unsure" and args.keep_unsure)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(decisions[c.id], ensure_ascii=False) + "\n")

    by_id = {c.id: c for c in chunks}
    kept = [d for d in decisions.values() if d["keep"]]
    dropped = [d for d in decisions.values() if not d["keep"]]
    lines = [
        "# Curation review",
        "",
        f"kept {len(kept)} / {len(chunks)} chunks "
        f"({sum(d['words'] for d in kept)} of {sum(d['words'] for d in decisions.values())} words)",
        "",
        "Flip a decision by editing `keep` in " + str(out_path) + " (set `manual: true` so it survives re-runs).",
        "",
        "## Dropped",
        "",
    ]
    for d in dropped:
        preview = by_id[d["id"]].text[:240].replace("\n", " ")
        lines.append(f"- **{d['id']}** `{d['source']}` [{d['label']}] {', '.join(d['flags']) or ''} {d['reason']}\n  > {preview}")
    lines += ["", "## Kept but unsure-ish (confidence < 0.8)", ""]
    for d in kept:
        if d.get("confidence") is not None and d["confidence"] < 0.8:
            preview = by_id[d["id"]].text[:240].replace("\n", " ")
            lines.append(f"- **{d['id']}** `{d['source']}` conf {d['confidence']:.2f}: {d['reason']}\n  > {preview}")
    Path(args.review).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"kept {len(kept)}/{len(chunks)} chunks. decisions -> {out_path}, review -> {args.review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
