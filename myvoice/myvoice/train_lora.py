"""Fine-tune a small open model with LoRA on data/pairs.jsonl.

Learns neutral -> your voice. Defaults are tuned for a single consumer GPU
(8-16 GB) or Apple Silicon; on CPU use --base Qwen/Qwen2.5-0.5B-Instruct and
expect it to be slow. Requires requirements-train.txt.

    python -m myvoice.train_lora --epochs 3
    python -m myvoice.paraphrase --backend local "some text"

How much data: ~200 pairs gives a noticeable shift, 1000+ starts to feel
consistent. Use build_dataset --variants 2 or 3 to multiply pairs from the
same source text.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

LOCAL_SYSTEM = "Rewrite the user's text in the author's voice. Keep every fact and the order of points. Output only the rewritten text."


def build_messages(system: str, neutral: str, original: str | None = None) -> list[dict]:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": neutral}]
    if original is not None:
        msgs.append({"role": "assistant", "content": original})
    return msgs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--out", default="models/lora")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--val-split", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except ImportError as e:
        raise SystemExit("pip install -r requirements-train.txt") from e

    pairs = [json.loads(ln) for ln in Path(args.pairs).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(pairs) < 20:
        raise SystemExit(f"only {len(pairs)} pairs; run build_dataset on more samples first")
    random.seed(args.seed)
    random.shuffle(pairs)
    n_val = max(1, int(len(pairs) * args.val_split))
    val, train = pairs[:n_val], pairs[n_val:]
    print(f"{len(train)} train / {len(val)} val pairs, base {args.base}")

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype="auto", device_map="auto")
    model = get_peft_model(
        model,
        LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                   target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]),
    )
    model.print_trainable_parameters()

    def encode(p: dict) -> dict:
        # loss only on the assistant turn: prompt tokens get label -100
        prompt = tok.apply_chat_template(build_messages(LOCAL_SYSTEM, p["neutral"]), tokenize=False, add_generation_prompt=True)
        full = tok.apply_chat_template(build_messages(LOCAL_SYSTEM, p["neutral"], p["original"]), tokenize=False)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        f_ids = tok(full, add_special_tokens=False)["input_ids"][: args.max_len]
        labels = [-100] * min(len(p_ids), len(f_ids)) + f_ids[len(p_ids):]
        return {"input_ids": f_ids, "attention_mask": [1] * len(f_ids), "labels": labels}

    class DS(torch.utils.data.Dataset):
        def __init__(self, rows):
            self.rows = [encode(r) for r in rows]

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, i):
            return self.rows[i]

    def collate(batch):
        m = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id
        return {
            "input_ids": torch.tensor([b["input_ids"] + [pad] * (m - len(b["input_ids"])) for b in batch]),
            "attention_mask": torch.tensor([b["attention_mask"] + [0] * (m - len(b["attention_mask"])) for b in batch]),
            "labels": torch.tensor([b["labels"] + [-100] * (m - len(b["labels"])) for b in batch]),
        }

    use_cuda = torch.cuda.is_available()
    targs = TrainingArguments(
        output_dir=str(Path(args.out) / "checkpoints"),
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="no",
        bf16=use_cuda and torch.cuda.is_bf16_supported(),
        fp16=use_cuda and not torch.cuda.is_bf16_supported(),
        report_to=[],
        seed=args.seed,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=DS(train), eval_dataset=DS(val), data_collator=collate)
    trainer.train()
    print("final eval:", trainer.evaluate())

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    (out / "myvoice.json").write_text(json.dumps({"base_model": args.base, "pairs": len(pairs), "epochs": args.epochs}))
    print(f"saved adapter to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
