"""myvoice: paraphrase text into your own writing voice.

Pipeline:
    1. corpus.py        load + chunk your samples
    2. profile.py       extract a measurable style profile
    3. build_dataset.py Claude "neutralizes" each chunk -> (neutral, yours) pairs
    4. paraphrase.py    rewrite new text in your voice (Claude few-shot or local LoRA)
    5. train_lora.py    optional: fine-tune a small open model on the pairs
"""

__version__ = "0.1.0"
