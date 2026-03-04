from __future__ import annotations

"""
Phase 3 – Hybrid retrieval by intent.

Given a classification result and the user query, retrieves:
- Structured scheme facts (from mutual_fund_schemes) when intent is SCHEME_FACT
- Vector chunks (with optional page_type / scheme_slug filter) for RAG context
- A single source_url for the response
"""

from dataclasses import dataclass
from typing import List, Optional

from backend.config import IntentType
from backend.db import get_connection, init_db
from backend.intent_classifier import ClassificationResult, TOPIC_SOURCE_URLS
from backend.local_embeddings import embed_text
from backend.retrieval import RetrievedChunk, search_similar_chunks


@dataclass
class RetrievalResult:
    structured_facts: str
    chunks: List[RetrievedChunk]
    source_url: str
    refusal: bool


def _prioritize_canonical_url(
    chunks: List[RetrievedChunk],
    canonical_url: Optional[str],
) -> List[RetrievedChunk]:
    """
    If a canonical URL is known (e.g. reports/help page, MF overview page),
    move chunks from that URL to the front of the list while preserving
    relative order for others. This biases the top chunk toward the expected
    source without changing similarity scoring.
    """
    if not canonical_url or not chunks:
        return chunks
    primary: List[RetrievedChunk] = []
    secondary: List[RetrievedChunk] = []
    for ch in chunks:
        if ch.url == canonical_url:
            primary.append(ch)
        else:
            secondary.append(ch)
    return primary + secondary


def _get_scheme_row(scheme_slug: str) -> Optional[dict]:
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT scheme_name, underlying_url, expense_ratio, exit_load,
                   min_sip_amount, min_lumpsum_amount, risk_level, benchmark_index,
                   category, amc_name
            FROM mutual_fund_schemes
            WHERE scheme_slug = ?
            """,
            (scheme_slug,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "scheme_name": row[0],
            "underlying_url": row[1],
            "expense_ratio": row[2],
            "exit_load": row[3],
            "min_sip_amount": row[4],
            "min_lumpsum_amount": row[5],
            "risk_level": row[6],
            "benchmark_index": row[7],
            "category": row[8],
            "amc_name": row[9],
        }
    finally:
        conn.close()


def retrieve(
    user_message: str,
    classification: ClassificationResult,
    top_k: int = 5,
) -> RetrievalResult:
    intent = classification.intent_type
    source_url = classification.source_url_hint or "https://groww.in/p/expense-ratio"

    if intent == IntentType.ADVICE_OR_OPINION:
        return RetrievalResult(
            structured_facts="",
            chunks=[],
            source_url=classification.source_url_hint or source_url,
            refusal=True,
        )

    if intent == IntentType.OUT_OF_SCOPE:
        return RetrievalResult(
            structured_facts="",
            chunks=[],
            source_url=source_url,
            refusal=True,
        )

    structured_facts = ""
    chunks: List[RetrievedChunk] = []

    if intent == IntentType.SCHEME_FACT and classification.scheme_candidate:
        scheme_slug = classification.scheme_candidate
        row = _get_scheme_row(scheme_slug)
        if row:
            source_url = row["underlying_url"] or source_url
            parts = [f"Scheme: {row['scheme_name'] or scheme_slug}"]
            for key in ["expense_ratio", "exit_load", "min_sip_amount", "min_lumpsum_amount", "risk_level", "benchmark_index", "category", "amc_name"]:
                val = row.get(key)
                if val:
                    parts.append(f"{key}: {val}")
            structured_facts = "\n".join(parts)
        else:
            # Fallback: if we don't have a structured row (e.g. scheme page
            # could not be fetched), still prefer the canonical scheme URL
            # as source_url so responses point to the most relevant page.
            source_url = f"https://groww.in/mutual-funds/{scheme_slug}"
        query_emb = embed_text(user_message)
        chunks = search_similar_chunks(
            query_emb,
            top_k=top_k,
            scheme_slug=scheme_slug,
        )
        if not chunks:
            chunks = search_similar_chunks(query_emb, top_k=top_k)

    elif intent in (IntentType.GENERAL_DEFINITION, IntentType.FEES_CHARGES):
        source_url = classification.source_url_hint or source_url
        query_emb = embed_text(user_message)
        chunks = search_similar_chunks(
            query_emb,
            top_k=top_k,
            page_types=["definition", "blog", "help"],
        )
        if not chunks:
            chunks = search_similar_chunks(query_emb, top_k=top_k)
        chunks = _prioritize_canonical_url(chunks, classification.source_url_hint)

    else:
        # OTHER_FACTUAL and any remaining queries.
        query_emb = embed_text(user_message)

        # If the classifier provided a topic-level hint, restrict candidates to
        # relevant page types to improve grounding before falling back.
        if classification.source_url_hint == TOPIC_SOURCE_URLS.get("reports"):
            # Statement / reports questions -> help/reports page and other help pages.
            chunks = search_similar_chunks(
                query_emb,
                top_k=top_k,
                page_types=["help"],
            )
        elif classification.source_url_hint == TOPIC_SOURCE_URLS.get(
            "mutual_funds_overview"
        ):
            # Compliance / safety questions -> mutual funds overview / definitions.
            chunks = search_similar_chunks(
                query_emb,
                top_k=top_k,
                page_types=["definition", "help"],
            )
        else:
            chunks = []

        if not chunks:
            chunks = search_similar_chunks(query_emb, top_k=top_k)
        chunks = _prioritize_canonical_url(chunks, classification.source_url_hint)
        # Only fall back to the top chunk URL when we do not already have
        # a topic-level source_url_hint from the classifier. This keeps
        # answers anchored on the expected canonical page when a hint exists.
        if chunks and not classification.source_url_hint:
            source_url = chunks[0].url

    return RetrievalResult(
        structured_facts=structured_facts,
        chunks=chunks,
        source_url=source_url,
        refusal=False,
    )


__all__ = ["RetrievalResult", "retrieve"]
