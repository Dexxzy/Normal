from myvoice.curate import heuristic_flags, heuristic_keep

INSTRUCTIONS = """Assignment 3: Personal Essay
Instructions:
1. Write a 500 word essay about a formative experience.
2. Include at least two sources.
3. Submit by Friday. Due: March 3"""

ESSAY = "so the summer i turned sixteen my dad decided we were going to fix the boat ourselves. i thought it was a terrible idea and said so, repeatedly, but he had that look."


def test_instruction_block_flagged():
    flags = heuristic_flags(INSTRUCTIONS)
    assert "instruction-vocab" in flags
    assert "imperative-list" in flags
    assert not heuristic_keep(flags)


def test_essay_kept():
    assert heuristic_keep(heuristic_flags(ESSAY))


def test_placeholders_flagged():
    assert not heuristic_keep(heuristic_flags("Dear [Insert Name], thank you for your ______ application to {{company}}. " * 3))
