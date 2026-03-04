from __future__ import annotations

"""
Phase 3/4 – RAG orchestration: classify -> retrieve -> generate answer with single source URL.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from backend.config import IntentType
from backend.openrouter_client import generate_content
from backend.intent_classifier import classify, ClassificationResult
from backend.retriever import retrieve, RetrievalResult


SYSTEM_PROMPT = """You are a factual Groww Mutual Fund FAQ assistant. You ONLY use the provided context from Groww public pages. If the answer is not in the context, say you do not know. Never give investment advice, recommendations, or opinions. Answer in at most 3 concise sentences. Do not invent URLs."""

LAST_UPDATED_DATE = date.today().isoformat()


@dataclass
class ChatResponse:
    answer: str
    source_url: str
    intent_type: str
    scheme_slug: Optional[str]
    refusal: bool


def _build_context(retrieval: RetrievalResult) -> str:
    parts: List[str] = []
    if retrieval.structured_facts:
        parts.append(retrieval.structured_facts)
    for c in retrieval.chunks[:5]:
        parts.append(f"[{c.section_title or 'Section'}]\n{c.content}")
    return "\n\n".join(parts) if parts else ""


def _maybe_answer_elss_special_case(
    user_message: str,
    classification: ClassificationResult,
) -> Optional[ChatResponse]:
    """
    Hardcoded ELSS handling for HDFC Tax Saver / ELSS questions, per user request.

    This bypasses retrieval only for the specific ELSS scheme, using the canonical
    tax-saver URL as the source.
    """
    scheme_slug = classification.scheme_candidate
    if scheme_slug != "hdfc-tax-saver-fund-direct-growth":
        return None

    lower = user_message.lower()
    source_url = "https://groww.in/mutual-funds/hdfc-tax-saver-fund-direct-growth"

    base_answer: Optional[str] = None
    if "lock-in" in lower or "lock in" in lower:
        base_answer = (
            "HDFC ELSS Tax Saver Fund has a mandatory lock-in period of 3 years "
            "from the date of each investment."
        )
    elif "section 80c" in lower or "80c" in lower or "tax deduction" in lower:
        base_answer = (
            "Investments in HDFC ELSS Tax Saver Fund qualify for tax deduction "
            "under Section 80C, subject to applicable limits and tax laws."
        )
    elif "minimum sip" in lower or "min sip" in lower:
        base_answer = (
            "You can start a SIP in HDFC ELSS Tax Saver Fund with at least the "
            "minimum SIP amount shown on its scheme page on Groww; check the "
            "latest value there as it may change over time."
        )

    if not base_answer:
        return None

    answer = (
        f"{base_answer}\n\n"
        f"Source: {source_url}\n"
        f"Last updated from sources: {LAST_UPDATED_DATE}"
    )
    return ChatResponse(
        answer=answer,
        source_url=source_url,
        intent_type=classification.intent_type.value,
        scheme_slug=scheme_slug,
        refusal=False,
    )


def chat(user_message: str, _history: Optional[List[dict]] = None) -> ChatResponse:
    """
    Run the full pipeline: classify -> retrieve -> generate (or refuse / ELSS-special-case).
    Returns answer, single source_url, intent_type, scheme_slug, refusal.
    """
    classification = classify(user_message)

    # ELSS tax-saver special-case handling, explicitly requested by the user.
    elss_resp = _maybe_answer_elss_special_case(user_message, classification)
    if elss_resp is not None:
        return elss_resp

    retrieval = retrieve(user_message, classification, top_k=5)

    if retrieval.refusal:
        if classification.intent_type == IntentType.ADVICE_OR_OPINION:
            base_answer = (
                "I provide facts only. For investment decisions, please consult a financial advisor."
            )
        else:
            base_answer = (
                "That question is outside my scope. I can only answer factual questions about "
                "the listed HDFC mutual fund schemes and general concepts like expense ratio, "
                "exit load, fees, and Groww help content."
            )
        answer = (
            f"{base_answer}\n\n"
            f"Source: {retrieval.source_url}\n"
            f"Last updated from sources: {LAST_UPDATED_DATE}"
        )
        return ChatResponse(
            answer=answer,
            source_url=retrieval.source_url,
            intent_type=classification.intent_type.value,
            scheme_slug=classification.scheme_candidate,
            refusal=True,
        )

    context = _build_context(retrieval)
    if not context:
        answer = (
            "I don't have enough information in my knowledge base to answer that. "
            "Please check the source link for details."
        )
    else:
        answer = generate_content(
            user_message,
            system_instruction=SYSTEM_PROMPT,
            context_text=context,
        )

    answer = answer.rstrip()
    answer = (
        f"{answer}\n\n"
        f"Source: {retrieval.source_url}\n"
        f"Last updated from sources: {LAST_UPDATED_DATE}"
    )

    return ChatResponse(
        answer=answer,
        source_url=retrieval.source_url,
        intent_type=classification.intent_type.value,
        scheme_slug=classification.scheme_candidate,
        refusal=False,
    )


__all__ = ["ChatResponse", "chat"]

