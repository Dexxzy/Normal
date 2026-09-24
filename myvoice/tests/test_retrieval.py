from myvoice.retrieval import Retriever


def test_retriever_ranks_by_overlap():
    docs = ["cats sleep all day on the couch", "the stock market fell sharply today", "my cat naps on the sofa constantly"]
    r = Retriever(docs)
    assert r.top("cat sleeping on the couch", k=2)[0] in (0, 2)
    assert 1 not in r.top("cat sleeping on the couch", k=2)


def test_retriever_handles_empty_query():
    r = Retriever(["a b c", "d e f"])
    assert len(r.top("", k=5)) == 2
