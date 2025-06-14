from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from services.vector_search import VectorStore


def test_search_returns_expected_results(tmp_path: Path) -> None:
    store = VectorStore(path=tmp_path)
    dim = 1536
    index = faiss.IndexFlatL2(dim)
    embeddings = np.zeros((3, dim), dtype="float32")
    embeddings[0, 0] = 1.0
    embeddings[1, 1] = 1.0
    embeddings[2, 2] = 1.0
    index.add(embeddings)

    store.index = index
    store.texts = ["alpha", "beta", "gamma"]

    query_vec = np.zeros((1, dim), dtype="float32")
    query_vec[0, 0] = 1.0

    with patch.object(store, "_embed", return_value=query_vec):
        results = store.search("alpha", k=2)

    assert results
    assert results[0] == "alpha"
    assert len(results) == 2


def test_search_empty_index_returns_empty(tmp_path: Path) -> None:
    store = VectorStore(path=tmp_path)
    with patch.object(store, "_embed") as embed_mock:
        results = store.search("anything")
    assert results == []
    embed_mock.assert_not_called()
