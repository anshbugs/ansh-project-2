from __future__ import annotations

"""
Prototype retrieval utilities using the Phase 2 embedding index.

This is a simple in-memory cosine similarity search over embeddings stored in
the kb_chunk_embeddings table. It will be used and extended in later phases
when wiring up the full backend API.
"""

import json
import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from backend.db import get_connection, init_db


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


def _load_all_embeddings() -> List[tuple]:
    """
    Load (chunk_id, embedding_vector) pairs from the DB.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT chunk_id, embedding_json FROM kb_chunk_embeddings;")
        rows = cur.fetchall()
        result: List[tuple] = []
        for chunk_id, emb_json in rows:
            vec = np.array(json.loads(emb_json), dtype=float)
            result.append((chunk_id, vec))
        return result
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

    If page_types is set, only chunks with page_type in that list are considered.
    If scheme_slug is set, only chunks with that scheme_slug are considered.
    """
    init_db()
    all_embs = _load_all_embeddings()
    if not all_embs:
        return []

    if page_types is not None or scheme_slug is not None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT chunk_id, page_type, scheme_slug FROM kb_chunks"
            )
            allowed_ids = set()
            for cid, pt, ss in cur.fetchall():
                if page_types is not None and pt not in page_types:
                    continue
                if scheme_slug is not None and ss != scheme_slug:
                    continue
                allowed_ids.add(cid)
        finally:
            conn.close()
        all_embs = [(cid, vec) for cid, vec in all_embs if cid in allowed_ids]

    if not all_embs:
        return []

    q = np.array(query_embedding, dtype=float)
    q_len = q.shape[0]
    scored: List[tuple[str, float]] = []
    for cid, vec in all_embs:
        # Skip any embeddings with mismatched dimensionality (e.g. after model changes)
        if vec.shape[0] != q_len:
            continue
        score = _cosine_similarity(q, vec)
        if not math.isnan(score):
            scored.append((cid, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]
    top_ids = [cid for cid, _ in top]
    meta_chunks = _load_chunk_metadata(top_ids)

    score_by_id = {cid: s for cid, s in top}
    for ch in meta_chunks:
        ch.score = score_by_id.get(ch.chunk_id, 0.0)
    meta_chunks.sort(key=lambda c: c.score, reverse=True)
    return meta_chunks


__all__ = ["RetrievedChunk", "search_similar_chunks"]

