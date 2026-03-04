from __future__ import annotations

"""
Local embeddings client using sentence-transformers.

Model: all-MiniLM-L6-v2

Embeddings are computed fully locally; no external API is used.
"""

from functools import lru_cache
from typing import List


@lru_cache(maxsize=1)
def _get_model():
    """
    Load the sentence-transformers model once per process.

    We import SentenceTransformer lazily so that missing dependencies raise a
    clear, actionable error instead of a generic ImportError at import time.
    """
    import logging
    import os

    # Suppress verbose "LOAD REPORT" / UNEXPECTED key messages from transformers
    # (e.g. embeddings.position_ids with all-MiniLM-L6-v2). Model works correctly.
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    for _name in ("transformers", "sentence_transformers"):
        logging.getLogger(_name).setLevel(logging.ERROR)

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Please run `python -m pip install sentence-transformers` and retry."
        ) from exc

    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Batch-embed a list of texts using the local model.

    Returns:
        List of embeddings, each as a list[float].
    """
    if not texts:
        return []
    model = _get_model()
    # Return plain Python lists so they can be JSON-serialised into SQLite.
    emb = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [vec.tolist() for vec in emb]


def embed_text(text: str) -> List[float]:
    """
    Convenience wrapper to embed a single text.
    """
    return embed_texts([text])[0]


__all__ = ["embed_texts", "embed_text"]

