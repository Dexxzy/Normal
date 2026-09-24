"""Rewrite text in your voice.

Two backends:

  claude  (default) no training. Builds a prompt from your style card plus the
          most relevant (neutral -> yours) pairs retrieved from data/pairs.jsonl
          (falls back to raw sample chunks if you haven't built pairs yet).
          Best quality with a small corpus; costs an API call per paraphrase.

  local   the LoRA you trained with train_lora.py. Free after training,
          runs offline, but a 1-3B model captures surface style more than
          judgment; expect rougher output than the claude backend.

    python -m myvoice.paraphrase "text to rewrite"
    python -m myvoice.paraphrase --file draft.txt --backend local
    echo "text" | python -m myvoice.paraphrase -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .corpus import build_corpus
from .profile import build_profile, style_card
from .retrieval import Retriever

SYSTEM_TEMPLATE = """You rewrite text so it reads as if a specific person wrote it. You are not summarizing or editing for quality; you are translating from generic prose into their voice.

Hard rules:
- Keep every fact, claim, number, name, and the order of points. Nothing added, nothing dropped.
- Match their habits below even when they are "wrong" by textbook standards (lowercase, missing apostrophes, run-ons, sentence fragments). Do not clean them up.
- Do not exaggerate the voice into caricature. The examples show the real density of their tics; match that density, not more.
- Output only the rewritten text.

Measured habits of this writer:
{style_card}

Examples of the transformation (PLAIN is generic prose, THEIRS is how they actually wrote the same thing):

{examples}"""

RAW_EXAMPLE_TEMPLATE = """You rewrite text so it reads as if a specific person wrote it. Keep every fact and the order of points; change only the voice. Match their habits even when non-standard (lowercase, missing apostrophes, fragments). Do not exaggerate into caricature. Output only the rewritten text.

Measured habits of this writer:
{style_card}

Samples of their actual writing:

{examples}"""


def load_examples(pairs_path: Path, samples_dir: Path) -> tuple[list[dict], bool]:
    """Return (examples, paired). paired=True means neutral/original pairs."""
    if pairs_path.exists():
        pairs = [json.loads(ln) for ln in pairs_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        pairs = [p for p in pairs if p.get("variant", 0) == 0] or pairs
        if pairs:
            return pairs, True
    chunks = build_corpus(samples_dir)
    return [{"original": c.text} for c in chunks], False


def build_system(examples: list[dict], paired: bool, card: str, query: str, k: int) -> str:
    key = "neutral" if paired else "original"
    retr = Retriever([e[key] for e in examples])
    picked = [examples[i] for i in retr.top(query, k=k)]
    if paired:
        shown = "\n\n".join(f"PLAIN:\n{e['neutral']}\n\nTHEIRS:\n{e['original']}" for e in picked)
        return SYSTEM_TEMPLATE.format(style_card=card, examples=shown)
    shown = "\n\n".join(f"<sample>\n{e['original']}\n</sample>" for e in picked)
    return RAW_EXAMPLE_TEMPLATE.format(style_card=card, examples=shown)


def paraphrase_claude(text: str, *, samples: str, pairs: str, profile: str, model: str, k: int, effort: str) -> str:
    from .llm import complete, get_client

    prof_path = Path(profile)
    if prof_path.exists():
        prof = json.loads(prof_path.read_text(encoding="utf-8"))
    else:
        prof = build_profile(build_corpus(samples))
    card = style_card(prof)
    examples, paired = load_examples(Path(pairs), Path(samples))
    if not examples:
        raise SystemExit("no examples: add writing to samples/ (and ideally run build_dataset)")
    system = build_system(examples, paired, card, text, k)
    # cache_system=False: the retrieved examples change per query, so a cache
    # write would rarely be read back. Flip to True if you batch similar inputs.
    return complete(
        get_client(),
        system=system,
        user="Rewrite this in the writer's voice:\n\n" + text,
        model=model,
        effort=effort,
        max_tokens=4096,
        cache_system=False,
    )


def paraphrase_local(text: str, *, model_dir: str, max_new_tokens: int) -> str:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:  # pragma: no cover
        raise SystemExit("pip install -r requirements-train.txt for the local backend") from e
    from .train_lora import LOCAL_SYSTEM, build_messages

    cfg = json.loads((Path(model_dir) / "myvoice.json").read_text())
    tok = AutoTokenizer.from_pretrained(model_dir)
    base = AutoModelForCausalLM.from_pretrained(cfg["base_model"], torch_dtype="auto", device_map="auto")
    model = PeftModel.from_pretrained(base, model_dir).eval()
    prompt = tok.apply_chat_template(build_messages(LOCAL_SYSTEM, text), tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.8, top_p=0.95,
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="text to rewrite, or '-' for stdin")
    ap.add_argument("--file", help="read the text from a file")
    ap.add_argument("--backend", choices=["claude", "local"], default="claude")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--profile", default="data/profile.json")
    ap.add_argument("--model", default="claude-opus-5", help="claude backend model id")
    ap.add_argument("--model-dir", default="models/lora", help="local backend adapter dir")
    ap.add_argument("--examples", type=int, default=6, help="few-shot examples to retrieve")
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--max-new-tokens", type=int, default=600)
    args = ap.parse_args(argv)

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text == "-" or args.text is None:
        text = sys.stdin.read()
    else:
        text = args.text
    text = text.strip()
    if not text:
        raise SystemExit("nothing to rewrite")

    if args.backend == "claude":
        out = paraphrase_claude(text, samples=args.samples, pairs=args.pairs, profile=args.profile,
                                model=args.model, k=args.examples, effort=args.effort)
    else:
        out = paraphrase_local(text, model_dir=args.model_dir, max_new_tokens=args.max_new_tokens)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
