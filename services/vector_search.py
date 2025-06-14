"""Simple FAISS-based vector store wrapper for Vacalyser."""

from __future__ import annotations
from pathlib import Path
from typing import List

import faiss
import numpy as np
import openai  # type: ignore

from utils import config


class VectorStore:
    """FAISS index wrapper storing document embeddings."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Create a new store or load an existing one.

        Args:
            path: Optional directory path for the index files.
        """
        self.path = Path(path or config.VECTOR_STORE_PATH)
        self.index: faiss.IndexFlatL2 | None = None
        self.texts: list[str] = []
        self._load()

    def _load(self) -> None:
        """Load index and texts from ``self.path`` if available."""
        if (self.path / "index.bin").exists():
            self.index = faiss.read_index(str(self.path / "index.bin"))
            self.texts = (self.path / "texts.txt").read_text().split("\n\u0000")
        else:
            self.index = faiss.IndexFlatL2(1536)
            self.texts = []
            self.path.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        """Persist the index and texts to disk."""
        if self.index:
            faiss.write_index(self.index, str(self.path / "index.bin"))
            (self.path / "texts.txt").write_text("\n\u0000".join(self.texts))

    def _embed(self, texts: List[str]) -> np.ndarray:
        """Embed texts via OpenAI embeddings.

        Args:
            texts: List of texts to embed.

        Returns:
            Array of embeddings as ``float32`` vectors.
        """
        result = openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        vecs = np.array([d.embedding for d in result.data], dtype="float32")
        return vecs

    def add_texts(self, texts: List[str]) -> None:
        """Add new texts to the index and persist them."""
        if not texts:
            return
        embeddings = self._embed(texts)
        assert self.index is not None
        self.index.add(embeddings)
        self.texts.extend(texts)
        self._save()

    def search(self, query: str, k: int = 3) -> List[str]:
        """Return ``k`` texts most similar to ``query``.

        Args:
            query: Search query text.
            k: Number of results to return.

        Returns:
            List of stored texts ranked by similarity.
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        if not query:
            return []
        q_emb = self._embed([query])
        dists, idxs = self.index.search(q_emb, k)
        results = []
        for idx in idxs[0]:
            if 0 <= idx < len(self.texts):
                results.append(self.texts[idx])
        return results
