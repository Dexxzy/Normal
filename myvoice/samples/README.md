# samples/

Drop your own writing in here as `.txt` or `.md` files. Anything you wrote
yourself: emails, journal entries, blog posts, forum replies, DMs, essays,
commit messages if they're wordy. One file per document is easiest, but a
big dump file also works since everything gets chunked by paragraph.

What matters:

- **Volume.** Under ~5,000 words the local fine-tune won't learn much. The
  Claude few-shot path works with far less, since it just needs examples to
  imitate. 20,000+ words is where the LoRA starts sounding like you.
- **It's actually you.** Don't include quoted replies, pasted articles, or
  AI-assisted drafts. The model learns whatever is in here.
- **Match the register you want.** If you want casual paraphrases, feed it
  casual writing. Mixing formal and casual is fine; the profile will show
  the blend, and you can later split into separate sample dirs.

This README is skipped by the loader.
