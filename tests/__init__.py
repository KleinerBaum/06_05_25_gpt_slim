"""Test package setup with optional dependency stubs."""

from __future__ import annotations

import sys
import types


# -- optional dependency stubs -------------------------------------------------


def _install_fitz_stub() -> None:
    """Create a very small fitz stub providing the API used in tests."""

    mod = types.ModuleType("fitz")

    class _Page:
        def insert_text(self, *args, **kwargs) -> None:  # noqa: D401
            """Dummy insert_text doing nothing."""
            pass

    class _Doc:
        def new_page(self) -> _Page:
            return _Page()

        def tobytes(self) -> bytes:
            return b""

        def close(self) -> None:
            pass

    def _open(*args, **kwargs) -> _Doc:
        return _Doc()

    mod.open = _open  # type: ignore[attr-defined]
    sys.modules["fitz"] = mod


def _install_faiss_stub() -> None:
    """Provide a minimal FAISS-like interface for tests."""

    import numpy as np

    mod = types.ModuleType("faiss")

    class IndexFlatL2:
        def __init__(self, dim: int) -> None:
            self.dim = dim
            self.vecs = np.empty((0, dim), dtype="float32")

        def add(self, vecs: np.ndarray) -> None:
            self.vecs = np.vstack([self.vecs, vecs])

        def search(self, q_vec: np.ndarray, k: int):
            if self.vecs.size == 0:
                dists = np.empty((q_vec.shape[0], k), dtype="float32")
                idxs = np.full((q_vec.shape[0], k), -1, dtype="int64")
                return dists, idxs
            dists = np.linalg.norm(self.vecs[None, :] - q_vec[:, None], axis=2)
            idxs = np.argsort(dists, axis=1)[:, :k]
            topdists = np.take_along_axis(dists, idxs, axis=1)
            return topdists, idxs

        @property
        def ntotal(self) -> int:
            return self.vecs.shape[0]

    def read_index(path: str) -> IndexFlatL2:  # noqa: D401
        """Return a new empty index."""
        return IndexFlatL2(1536)

    def write_index(index: IndexFlatL2, path: str) -> None:  # noqa: D401
        """Dummy write_index that does nothing."""
        pass

    mod.IndexFlatL2 = IndexFlatL2  # type: ignore[attr-defined]
    mod.read_index = read_index  # type: ignore[attr-defined]
    mod.write_index = write_index  # type: ignore[attr-defined]
    sys.modules["faiss"] = mod


def _install_streamlit_stub() -> None:
    """Provide a thin streamlit runtime.secrets stub."""

    mod = types.ModuleType("streamlit")
    runtime = types.ModuleType("streamlit.runtime")
    secrets_mod = types.ModuleType("streamlit.runtime.secrets")

    class Secrets(dict):
        def _parse(self, *args, **kwargs) -> dict:
            return {}

    secrets_mod.Secrets = Secrets  # type: ignore[attr-defined]
    runtime.secrets = secrets_mod  # type: ignore[attr-defined]
    mod.runtime = runtime  # type: ignore[attr-defined]

    sys.modules["streamlit"] = mod
    sys.modules["streamlit.runtime"] = runtime
    sys.modules["streamlit.runtime.secrets"] = secrets_mod


for name, installer in (
    ("fitz", _install_fitz_stub),
    ("faiss", _install_faiss_stub),
    ("streamlit", _install_streamlit_stub),
):
    if name not in sys.modules:
        try:
            __import__(name)
        except ModuleNotFoundError:
            installer()

__all__: list[str] = []
