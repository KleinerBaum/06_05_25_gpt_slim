import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import openai


def test_vector_search_embed_uses_retry(monkeypatch):
    called = {}

    def fake_call_with_retry(func, *args, **kwargs):
        called["func"] = func
        return {"data": [{"embedding": [0.0] * 1536}]}

    monkeypatch.setattr(st, "secrets", {})
    from services import vector_search as vs

    monkeypatch.setattr(vs, "call_with_retry", fake_call_with_retry)
    VectorStore = vs.VectorStore

    store = VectorStore(path="/tmp/vector_store_test")
    vecs = store._embed(["test text"])

    assert called["func"] is openai.Embedding.create
    assert isinstance(vecs, np.ndarray)
    assert vecs.shape == (1, 1536)
