from myvoice.corpus import Chunk
from myvoice.profile import build_profile, style_card

CASUAL = "huh. think i could do this? i dont know. its late and im tired but yeah lets try it"
FORMAL = "The committee reviewed the proposal in detail. After careful consideration, it approved the budget; however, several members raised concerns."


def test_profile_detects_lowercase_and_dropped_apostrophes():
    p = build_profile([Chunk("1", "a", CASUAL)])
    assert p["casing"]["sentences_starting_lowercase"] >= 0.9
    assert p["casing"]["lowercase_i_share"] == 1.0
    assert p["apostrophe_less_contractions_per_1k_words"] > 0
    card = style_card(p)
    assert "lowercase 'i'" in card
    assert "drops apostrophes" in card


def test_profile_formal_text():
    p = build_profile([Chunk("1", "a", FORMAL)])
    assert p["casing"]["sentences_starting_lowercase"] == 0
    assert p["punctuation_per_1k_words"]["semicolon"] > 0
    assert "capital letter" in style_card(p)


def test_profile_requires_chunks():
    import pytest

    with pytest.raises(ValueError):
        build_profile([])
