import json
import zipfile

from myvoice.importers import claude_export, takeout_docs
from myvoice.importers._common import group_bursts, looks_like_prose
from myvoice.importers.imessage import decode_attributed_body
from myvoice.importers.mbox import strip_quotes


def test_looks_like_prose_rejects_code_and_logs():
    assert looks_like_prose("i think the plan is fine but we should double check the dates before we send it out")
    assert not looks_like_prose("def f(x):\n    return {x: [1,2,3]}\n" * 5)
    assert not looks_like_prose("\n".join(f"ERROR line {i} failed" for i in range(10)))


def test_group_bursts_merges_close_messages():
    items = [(0, "hey"), (30, "so i was thinking"), (60, "we should go"), (5000, "different topic")]
    assert group_bursts(items, gap_seconds=900) == ["hey so i was thinking we should go", "different topic"]


def test_decode_attributed_body_short():
    payload = "hello there".encode()
    blob = b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+" + bytes([len(payload)]) + payload + b"\x86"
    assert decode_attributed_body(blob) == "hello there"


def test_strip_quotes():
    text = "thanks, sounds good to me.\n\nOn Tue, Mar 3, 2026 at 9:00 AM Bob <bob@x.com> wrote:\n> hi\n> whatever"
    assert strip_quotes(text).strip() == "thanks, sounds good to me."


def test_claude_export_human_turns():
    convo = {"chat_messages": [{"sender": "human", "text": "a"}, {"sender": "assistant", "text": "b"},
                               {"sender": "human", "text": "", "content": [{"type": "text", "text": "c"}]}]}
    assert claude_export.human_turns(convo) == ["a", "c"]


def test_takeout_docx_and_end_to_end(tmp_path):
    take = tmp_path / "Takeout" / "Drive"
    take.mkdir(parents=True)
    xml = '<?xml version="1.0"?><w:document><w:body><w:p><w:r><w:t>first paragraph of my essay which goes on for a while so it is long enough.</w:t></w:r></w:p><w:p><w:r><w:t>second para &amp; more words here to pad things out for the minimum.</w:t></w:r></w:p></w:body></w:document>'
    with zipfile.ZipFile(take / "essay.docx", "w") as z:
        z.writestr("word/document.xml", xml)
    (take / "notes.txt").write_text("plain notes " * 40)
    (take / "sheet.xlsx").write_text("x")
    out = tmp_path / "samples"
    assert takeout_docs.main([str(take), "--out", str(out), "--min-words", "10"]) == 0
    written = sorted(p.name for p in out.iterdir())
    assert written == ["essay.txt", "notes.txt"]
    body = (out / "essay.txt").read_text()
    assert "first paragraph" in body and "\n\n" in body and "&" in body


def test_claude_export_end_to_end(tmp_path):
    data = [{"name": "Chat one", "chat_messages": [
        {"sender": "human", "text": "ok so here is my actual question about the thing i have been trying to build for weeks now, " * 8},
        {"sender": "assistant", "text": "sure"},
    ]}]
    src = tmp_path / "conversations.json"
    src.write_text(json.dumps(data))
    out = tmp_path / "out"
    assert claude_export.main([str(src), "--out", str(out)]) == 0
    assert (out / "Chat_one.txt").exists()
