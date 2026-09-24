# myvoice

Paraphrase any text into your own writing voice, from samples of stuff you
actually wrote. Self-contained; nothing here touches the rest of the repo.

## Can this work?

Yes, with one trick. You only have one side of the training pair (your text),
and "paraphrase into my voice" needs pairs of *plain text -> your version*.
So step 3 manufactures the plain side: Claude rewrites each chunk of your
writing into flat, neutral prose that keeps every fact. Now you have
(neutral, yours) pairs and the task is a normal supervised rewrite.

Two ways to use those pairs:

| backend | training | quality | cost | needs |
|---|---|---|---|---|
| `claude` | none, few-shot with retrieved pairs + a measured style card | best, especially with a small corpus | an API call per paraphrase | `pip install anthropic`, `ANTHROPIC_API_KEY` |
| `local` | LoRA on a 0.5B-3B open model | rougher; nails surface habits, weaker on judgment | free after training | GPU or Apple Silicon, `requirements-train.txt` |

Honest expectations: with ~10k words the Claude backend already sounds like
you. The local LoRA needs 20k+ words (a few hundred pairs minimum, 1000+ to
feel consistent) and a 1.5B model will never match a frontier model's
understanding of *why* you phrase things the way you do. Build the dataset
once and try both.

## Pipeline

```
samples/<source>/*.txt   your writing (importers fill this)
        |  1. corpus.py       chunk into 40-220 word passages
        |  2. curate.py       drop chunks that aren't your words (instructions, pastes, other people)
        |  3. build_dataset   Claude neutralizes each chunk -> data/pairs.jsonl
        |  4. profile.py      style card: sentence length, casing, punctuation habits, vocab
        v
   paraphrase.py --backend claude     (uses pairs + style card as few-shot)
   train_lora.py -> paraphrase.py --backend local
```

## Quick start

```bash
cd myvoice
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

# 1. get your writing in (see Importers below), or just drop .txt/.md files in samples/
python -m myvoice.corpus --samples samples          # how much do you have?

# 2. curate docs that mix your prose with other stuff (optional but recommended for Google Docs)
python -m myvoice.curate --samples samples/docs --trusted samples/imessage samples/claude --llm
#    -> read data/curation_review.md, flip any wrong calls in data/curation.jsonl

# 3. build training pairs (resumable; --limit 20 for a dry run first)
python -m myvoice.build_dataset --samples samples --variants 2

# 4. style profile
python -m myvoice.profile --samples samples

# 5. paraphrase
python -m myvoice.paraphrase "The meeting has been moved to Thursday because two people are traveling."
python -m myvoice.paraphrase --file draft.txt > draft_in_my_voice.txt
```

Costs: neutralizing is roughly 400 input + 300 output tokens per chunk. At the
default `claude-opus-5` that is about $1 per 100 chunks; pass
`--model claude-sonnet-5` to build_dataset and curate for a cheaper bulk run.

## Importers

All stdlib-only, so they run wherever the data is. Each writes to its own
`samples/<source>/` folder because texting, prompting, and document writing are
different registers. Profile them separately (`--samples samples/imessage`)
before deciding whether to mix.

**Google Docs** (this is the one that needs curation):
takeout.google.com, deselect all, tick Drive, set Documents format to TXT or
Markdown, export, unzip.
```bash
python -m myvoice.importers.takeout_docs ~/Downloads/Takeout
```

**iMessage** (Mac): give your terminal Full Disk Access first.
```bash
python -m myvoice.importers.imessage            # reads ~/Library/Messages/chat.db read-only
```
Only your sent messages; bursts within 15 min merge into one paragraph.

**claude.ai**: Settings, Privacy, Export data. Unzip the emailed archive.
```bash
python -m myvoice.importers.claude_export ~/Downloads/data-*/conversations.json
```

**Claude Code** local sessions:
```bash
python -m myvoice.importers.claude_code         # reads ~/.claude/projects
```

**Sent email** (Gmail Takeout, Sent label only):
```bash
python -m myvoice.importers.mbox ~/Downloads/Takeout/Mail/Sent.mbox --me you@gmail.com
```

## Curation: "a lot of my docs contain instructions or things not written by me"

`curate.py` works per chunk, not per document, so an assignment prompt at the
top of a doc gets dropped while your essay under it is kept.

1. **Heuristics** (free): numbered imperative lists, rubric and assignment
   vocabulary, `[insert name]` placeholders, `>` quoted blocks, title-case
   headers. Hard flags drop the chunk outright.
2. **Claude judge** (`--llm`): sees a handful of *trusted* chunks that are
   definitely you (your texts, your Claude prompts) and labels each candidate
   `author` / `instructions` / `other_person` / `pasted` / `template` /
   `unsure` with a confidence and a one-line reason. Rough spelling and
   lowercase are treated as evidence *for* you, not against.

Output is `data/curation.jsonl` plus a readable `data/curation_review.md`
listing everything dropped with a preview. Edit `keep` in the jsonl to
override; set `"manual": true` on that line and re-runs will respect it.
`build_dataset.py` reads the decisions automatically.

## Local fine-tune

```bash
pip install -r requirements-train.txt
python -m myvoice.train_lora --epochs 3                      # Qwen2.5-1.5B-Instruct, LoRA r=16
python -m myvoice.paraphrase --backend local "some text"
```
Loss is masked to the assistant turn only, so the model learns the rewrite,
not the prompt. On CPU use `--base Qwen/Qwen2.5-0.5B-Instruct`. Adapters land
in `models/lora/` (gitignored).

## Privacy

`samples/` is tracked by git by default, on the assumption this repo is your
private storage. If it is public, or ever might be, add `samples/` to
`.gitignore` before importing anything. `data/` and `models/` are already
ignored.

## Tests

```bash
python -m pytest
```
