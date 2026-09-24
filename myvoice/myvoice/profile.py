"""Extract a measurable style profile from the corpus.

The profile does two jobs: it tells *you* what your voice actually looks like
in numbers, and it becomes a "style card" that gets fed to the model so the
paraphrase has explicit targets (sentence length, casing, punctuation habits)
on top of the few-shot examples.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter

from .corpus import Chunk, split_sentences

STOPWORDS = set(
    """a an the and or but if then so of to in on at for with by from as is are was were be been
    being am i you he she it we they me him her us them my your his its our their this that these
    those there here not no yes do does did doing have has had having will would can could should
    shall may might must what which who whom whose when where why how all any some more most
    other such only own same than too very just also into over under out up down off about
    again further once because while until through between before after above below""".split()
)

CONTRACTION = re.compile(r"\b\w+'(s|re|ve|ll|d|t|m)\b", re.I)
NO_APOS_CONTRACTION = re.compile(r"\b(dont|cant|wont|im|ive|isnt|arent|didnt|doesnt|thats|youre|theyre|wasnt|couldnt|wouldnt|shouldnt)\b")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text)


def build_profile(chunks: list[Chunk], top_n: int = 30) -> dict:
    if not chunks:
        raise ValueError("no chunks; add some writing to samples/ first")

    sentences: list[str] = []
    paragraphs: list[str] = []
    for c in chunks:
        for p in c.text.split("\n\n"):
            paragraphs.append(p)
            sentences.extend(split_sentences(p))

    all_text = "\n\n".join(c.text for c in chunks)
    words = _tokens(all_text)
    lower_words = [w.lower() for w in words]
    n_words = max(len(words), 1)
    per_k = lambda n: round(1000 * n / n_words, 2)  # noqa: E731

    sent_lens = [len(s.split()) for s in sentences] or [0]
    para_lens = [len(p.split()) for p in paragraphs] or [0]

    starts_lower = sum(1 for s in sentences if s and s[0].isalpha() and s[0].islower())
    lone_i = sum(1 for w in words if w == "i")
    cap_i = sum(1 for w in words if w == "I")

    contractions = len(CONTRACTION.findall(all_text))
    no_apos = len(NO_APOS_CONTRACTION.findall(all_text.lower()))

    punct = {
        "comma": all_text.count(","),
        "period": all_text.count("."),
        "question": all_text.count("?"),
        "exclamation": all_text.count("!"),
        "semicolon": all_text.count(";"),
        "colon": all_text.count(":"),
        "em_dash": all_text.count("—") + all_text.count(" -- ") + all_text.count(" - "),
        "ellipsis": all_text.count("...") + all_text.count("…"),
        "parens": all_text.count("("),
        "quotes": all_text.count('"'),
    }
    n_sent = max(len(sentences), 1)
    ends_no_period = sum(1 for s in sentences if s and s[-1] not in ".!?")

    content = Counter(w for w in lower_words if w not in STOPWORDS and len(w) > 2)
    openers = Counter(s.split()[0].lower().strip(",.") for s in sentences if s.split())
    bigrams = Counter(
        f"{a} {b}" for a, b in zip(lower_words, lower_words[1:]) if not (a in STOPWORDS and b in STOPWORDS)
    )

    return {
        "corpus": {
            "chunks": len(chunks),
            "words": n_words,
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
        },
        "sentence_length": {
            "mean": round(statistics.mean(sent_lens), 1),
            "median": statistics.median(sent_lens),
            "stdev": round(statistics.pstdev(sent_lens), 1),
            "share_under_8_words": round(sum(1 for n in sent_lens if n < 8) / n_sent, 2),
            "share_over_25_words": round(sum(1 for n in sent_lens if n > 25) / n_sent, 2),
        },
        "paragraph_length": {
            "mean": round(statistics.mean(para_lens), 1),
            "median": statistics.median(para_lens),
        },
        "casing": {
            "sentences_starting_lowercase": round(starts_lower / n_sent, 2),
            "lowercase_i_share": round(lone_i / max(lone_i + cap_i, 1), 2),
        },
        "contractions_per_1k_words": per_k(contractions),
        "apostrophe_less_contractions_per_1k_words": per_k(no_apos),
        "sentences_without_end_punctuation": round(ends_no_period / n_sent, 2),
        "punctuation_per_1k_words": {k: per_k(v) for k, v in punct.items()},
        "avg_word_length": round(sum(len(w) for w in words) / n_words, 2),
        "top_words": content.most_common(top_n),
        "top_sentence_openers": openers.most_common(15),
        "top_bigrams": bigrams.most_common(20),
    }


def style_card(profile: dict) -> str:
    """Render the profile as plain-English guidance for a model prompt."""
    sl = profile["sentence_length"]
    cs = profile["casing"]
    pk = profile["punctuation_per_1k_words"]
    lines = [
        f"- Sentences average {sl['mean']} words (median {sl['median']}); "
        f"{int(sl['share_under_8_words']*100)}% are under 8 words and "
        f"{int(sl['share_over_25_words']*100)}% are over 25.",
        f"- Paragraphs average {profile['paragraph_length']['mean']} words.",
    ]
    if cs["sentences_starting_lowercase"] >= 0.3:
        lines.append(
            f"- {int(cs['sentences_starting_lowercase']*100)}% of sentences start lowercase; "
            "the author mostly does not capitalize sentence starts."
        )
    elif cs["sentences_starting_lowercase"] >= 0.05:
        lines.append("- Occasionally starts a sentence lowercase; casual about capitalization.")
    else:
        lines.append("- Sentences start with a capital letter.")
    if cs["lowercase_i_share"] >= 0.5:
        lines.append("- Writes the pronoun as lowercase 'i'.")
    if profile["apostrophe_less_contractions_per_1k_words"] > 2:
        lines.append("- Often drops apostrophes in contractions (dont, im, cant).")
    c = profile["contractions_per_1k_words"] + profile["apostrophe_less_contractions_per_1k_words"]
    lines.append(
        "- Uses contractions " + ("heavily." if c > 25 else "moderately." if c > 8 else "rarely.")
    )
    if profile["sentences_without_end_punctuation"] > 0.2:
        lines.append("- Frequently leaves off the final period.")
    habits = []
    if pk["ellipsis"] > 3:
        habits.append("ellipses")
    if pk["em_dash"] > 3:
        habits.append("dashes")
    if pk["parens"] > 3:
        habits.append("parentheticals")
    if pk["exclamation"] > 5:
        habits.append("exclamation marks")
    if pk["question"] > 8:
        habits.append("rhetorical questions")
    if pk["semicolon"] > 2:
        habits.append("semicolons")
    if habits:
        lines.append("- Punctuation habits: " + ", ".join(habits) + ".")
    else:
        lines.append("- Plain punctuation: mostly periods and commas.")
    openers = ", ".join(w for w, _ in profile["top_sentence_openers"][:8])
    lines.append(f"- Common sentence openers: {openers}.")
    words = ", ".join(w for w, _ in profile["top_words"][:15])
    lines.append(f"- Characteristic vocabulary: {words}.")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    from .corpus import build_corpus

    ap = argparse.ArgumentParser(description="Build a style profile from samples/.")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default="data/profile.json")
    args = ap.parse_args()
    prof = build_profile(build_corpus(args.samples))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(prof, indent=2), encoding="utf-8")
    print(style_card(prof))
    print(f"\nwrote {args.out}")
