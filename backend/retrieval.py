from __future__ import annotations

"""
Prototype retrieval utilities using the Phase 2 embedding index.

Embeddings are loaded in batches during search (lazy, only when chat is called),
so the server does not load them at startup. This keeps memory low on Render.
"""

import json
import math
from dataclasses import dataclass
from typing import Generator, List, Optional, Set

import numpy as np

from backend.db import get_connection, init_db


# Load embeddings in batches to bound memory (no full load at startup).
EMBEDDING_BATCH_SIZE = 300


@dataclass
class RetrievedChunk:
    chunk_id: str
    url: str
    page_type: str
    scheme_slug: Optional[str]
    section_title: Optional[str]
    content: str
    score: float


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _get_allowed_chunk_ids(
    page_types: Optional[List[str]] = None,
    scheme_slug: Optional[str] = None,
) -> Optional[Set[str]]:
    """Return set of chunk_ids that pass filters, or None for no filter (all chunks)."""
    if page_types is None and scheme_slug is None:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT chunk_id, page_type, scheme_slug FROM kb_chunks")
        allowed = set()
        for cid, pt, ss in cur.fetchall():
            if page_types is not None and pt not in page_types:
                continue
            if scheme_slug is not None and ss != scheme_slug:
                continue
            allowed.add(cid)
        return allowed
    finally:
        conn.close()


def _load_embeddings_batched(
    allowed_ids: Optional[Set[str]] = None,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> Generator[List[tuple], None, None]:
    """
    Yield batches of (chunk_id, embedding_vector) from the DB.
    Keeps memory bounded to one batch instead of loading all embeddings.
    """
    conn = get_connection()
    try:
        if allowed_ids is not None and len(allowed_ids) == 0:
            return
        if allowed_ids is not None:
            id_list = list(allowed_ids)
            for i in range(0, len(id_list), batch_size):
                batch_ids = id_list[i : i + batch_size]
                placeholders = ",".join("?" for _ in batch_ids)
                cur = conn.cursor()
                cur.execute(
                    f"SELECT chunk_id, embedding_json FROM kb_chunk_embeddings WHERE chunk_id IN ({placeholders})",
                    batch_ids,
                )
                rows = cur.fetchall()
                result: List[tuple] = []
                for chunk_id, emb_json in rows:
                    vec = np.array(json.loads(emb_json), dtype=float)
                    result.append((chunk_id, vec))
                if result:
                    yield result
        else:
            cur = conn.cursor()
            cur.execute("SELECT chunk_id, embedding_json FROM kb_chunk_embeddings")
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                result = []
                for chunk_id, emb_json in rows:
                    vec = np.array(json.loads(emb_json), dtype=float)
                    result.append((chunk_id, vec))
                yield result
    finally:
        conn.close()


def _load_chunk_metadata(chunk_ids: List[str]) -> List[RetrievedChunk]:
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT chunk_id, url, page_type, scheme_slug, section_title, content
            FROM kb_chunks
            WHERE chunk_id IN ({placeholders});
            """,
            chunk_ids,
        )
        rows = cur.fetchall()
        by_id = {
            row[0]: (row[1], row[2], row[3], row[4], row[5])
            for row in rows
        }
    finally:
        conn.close()

    # The scores will be filled by the caller, so here we just map metadata.
    result: List[RetrievedChunk] = []
    for cid in chunk_ids:
        url, page_type, scheme_slug, section_title, content = by_id[cid]
        result.append(
            RetrievedChunk(
                chunk_id=cid,
                url=url,
                page_type=page_type,
                scheme_slug=scheme_slug,
                section_title=section_title,
                content=content,
                score=0.0,
            )
        )
    return result


def search_similar_chunks(
    query_embedding: List[float],
    top_k: int = 5,
    page_types: Optional[List[str]] = None,
    scheme_slug: Optional[str] = None,
) -> List[RetrievedChunk]:
    """
    Run cosine-similarity search over stored embeddings.
    Loads embeddings in batches (lazy); nothing is loaded at server startup.

    If page_types is set, only chunks with page_type in that list are considered.
    If scheme_slug is set, only chunks with that scheme_slug are considered.
    """
    init_db()
    allowed_ids = _get_allowed_chunk_ids(page_types=page_types, scheme_slug=scheme_slug)

    q = np.array(query_embedding, dtype=float)
    q_len = q.shape[0]
    scored: List[tuple[str, float]] = []

    for batch in _load_embeddings_batched(allowed_ids=allowed_ids):
        for cid, vec in batch:
            if vec.shape[0] != q_len:
                continue
            score = _cosine_similarity(q, vec)
            if not math.isnan(score):
                scored.append((cid, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]
    if not top:
        return []

    top_ids = [cid for cid, _ in top]
    meta_chunks = _load_chunk_metadata(top_ids)
    score_by_id = {cid: s for cid, s in top}
    for ch in meta_chunks:
        ch.score = score_by_id.get(ch.chunk_id, 0.0)
    meta_chunks.sort(key=lambda c: c.score, reverse=True)
    return meta_chunks


__all__ = ["RetrievedChunk", "search_similar_chunks"]

