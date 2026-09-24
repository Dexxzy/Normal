from myvoice.corpus import build_corpus, chunk_text, paragraphs, split_sentences


def test_split_sentences_basic():
    assert split_sentences("hi there. how are you? fine!") == ["hi there.", "how are you?", "fine!"]


def test_paragraphs_unwrap_soft_lines():
    text = "line one\nline two\n\nsecond para"
    assert paragraphs(text) == ["line one line two", "second para"]


def test_chunk_merges_short_paragraphs():
    text = "\n\n".join(["word " * 10] * 8)  # eight 10-word paras
    chunks = chunk_text(text, min_words=40, max_words=100)
    assert len(chunks) == 2
    assert [len(c.split()) for c in chunks] == [40, 40]


def test_chunk_splits_long_paragraph_at_sentences():
    text = " ".join(f"sentence number {i} is here." for i in range(60))  # ~300 words, one paragraph
    chunks = chunk_text(text, min_words=40, max_words=100)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c.split()) <= 100
        assert c.endswith(".")


def test_tiny_sample_still_yields_a_chunk():
    assert chunk_text("just a few words here.") == ["just a few words here."]


def test_build_corpus_skips_readme_and_ids_stable(tmp_path):
    (tmp_path / "README.md").write_text("ignore me " * 50)
    (tmp_path / "a.txt").write_text("hello there this is me writing. " * 20)
    (tmp_path / "b.pdf").write_text("nope")
    c1 = build_corpus(tmp_path)
    c2 = build_corpus(tmp_path)
    assert [c.source for c in c1] == ["a.txt"]
    assert [c.id for c in c1] == [c.id for c in c2]
