from __future__ import annotations

"""
Phase 3 – Intent classification and entity extraction.

Rule-based classifier that maps the latest user message to:
- intent_type (SCHEME_FACT, GENERAL_DEFINITION, FEES_CHARGES, etc.)
- requested_attributes (for scheme facts)
- scheme_candidate (slug from mutual_fund_schemes)
- source_url_hint (canonical URL for topic-level queries)
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from backend.config import (
    ADVICE_KEYWORDS,
    IntentType,
    SUPPORTED_SCHEME_ATTRIBUTES,
)
from backend.db import get_connection, init_db


# Phrases that map to scheme slugs (partial match on user query)
SCHEME_KEYWORDS: List[tuple[str, str]] = [
    ("hdfc mid cap", "hdfc-mid-cap-fund-direct-growth"),
    ("hdfc mid-cap", "hdfc-mid-cap-fund-direct-growth"),
    ("mid cap fund", "hdfc-mid-cap-fund-direct-growth"),
    ("hdfc equity", "hdfc-equity-fund-direct-growth"),
    ("hdfc arbitrage", "hdfc-arbitrage-fund-direct-growth"),
    ("hdfc liquid", "hdfc-liquid-fund-direct-growth"),
    ("hdfc value", "hdfc-value-fund-direct-plan-growth"),
    ("value fund", "hdfc-value-fund-direct-plan-growth"),
    ("hdfc tax saver", "hdfc-tax-saver-fund-direct-growth"),
    ("hdfc elss", "hdfc-tax-saver-fund-direct-growth"),
    ("elss tax saver", "hdfc-tax-saver-fund-direct-growth"),
]

# Attribute keywords -> internal attribute name
ATTRIBUTE_KEYWORDS: List[tuple[str, str]] = [
    ("expense ratio", "expense_ratio"),
    ("exit load", "exit_load"),
    ("minimum sip", "min_sip_amount"),
    ("min sip", "min_sip_amount"),
    ("sip amount", "min_sip_amount"),
    ("minimum investment", "min_sip_amount"),
    ("lumpsum", "min_lumpsum_amount"),
    ("lump sum", "min_lumpsum_amount"),
    ("risk level", "risk_level"),
    ("riskometer", "risk_level"),
    ("benchmark", "benchmark_index"),
    ("category", "category"),
    ("amc", "amc_name"),
]

# Topic -> canonical URL for source_url
TOPIC_SOURCE_URLS = {
    "expense_ratio": "https://groww.in/p/expense-ratio",
    "exit_load": "https://groww.in/p/exit-load-in-mutual-funds",
    "fees": "https://groww.in/blog/mutual-fund-fees-and-charges",
    "charges": "https://groww.in/blog/mutual-fund-fees-and-charges",
    "redeem": "https://groww.in/help/mutual-funds/order/what-are-the-charges-applicable-for-redeeming--53",
    "redeeming": "https://groww.in/help/mutual-funds/order/what-are-the-charges-applicable-for-redeeming--53",
    "reports": "https://groww.in/help/mutual-funds/reports",
    "mutual_funds_overview": "https://groww.in/p/mutual-funds",
}


@dataclass
class ClassificationResult:
    intent_type: IntentType
    requested_attributes: List[str]
    scheme_candidate: Optional[str]
    source_url_hint: Optional[str]
    confidence: float


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _detect_advice_or_opinion(query: str) -> bool:
    q = _normalize(query)
    return any(kw in q for kw in ADVICE_KEYWORDS)


def _resolve_scheme_slug(query: str) -> Optional[str]:
    q = _normalize(query)
    for phrase, slug in SCHEME_KEYWORDS:
        if phrase in q:
            return slug
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT scheme_slug, scheme_name FROM mutual_fund_schemes WHERE scheme_slug IS NOT NULL"
        )
        for slug, name in cur.fetchall():
            if name and _normalize(name) in q:
                return slug
            if slug and slug.replace("-", " ") in q:
                return slug
    finally:
        conn.close()
    return None


def _extract_attributes(query: str) -> List[str]:
    q = _normalize(query)
    found: List[str] = []
    for phrase, attr in ATTRIBUTE_KEYWORDS:
        if phrase in q and attr not in found and attr in SUPPORTED_SCHEME_ATTRIBUTES:
            found.append(attr)
    return found


def _is_definition_or_fees_query(query: str) -> bool:
    q = _normalize(query)
    definition_patterns = [
        "what is expense ratio",
        "what is exit load",
        "expense ratio meaning",
        "exit load meaning",
        "fees and charges",
        "mutual fund charges",
        "charges for redeeming",
        "redeeming charges",
    ]
    return any(p in q for p in definition_patterns) or bool(
        re.search(r"what (is|are) .*(expense|exit load|fee|charge)", q)
    )


def _is_statement_query(query: str) -> bool:
    q = _normalize(query)
    statement_keywords = [
        "mutual fund statement",
        "capital gains statement",
        "capital gain statement",
        "transaction history",
        "tax documents",
        "tax document",
        "groww reports",
        "reports section",
        "download statement",
    ]
    return any(k in q for k in statement_keywords)


def _is_compliance_query(query: str) -> bool:
    q = _normalize(query)
    patterns = [
        "guarantee returns",
        "guaranteed returns",
        "returns be negative",
        "negative returns",
        "risk-free",
        "risk free",
        "investment risk-free",
        "returns fixed",
        "fixed returns",
        "market linked",
    ]
    return any(p in q for p in patterns)


def _topic_source_hint(query: str) -> Optional[str]:
    q = _normalize(query)
    if "expense ratio" in q:
        return TOPIC_SOURCE_URLS["expense_ratio"]
    if "exit load" in q:
        return TOPIC_SOURCE_URLS["exit_load"]
    if "redeem" in q or "redeeming" in q:
        return TOPIC_SOURCE_URLS["redeem"]
    if "fee" in q or "charge" in q:
        return TOPIC_SOURCE_URLS["fees"]
    if _is_statement_query(q):
        return TOPIC_SOURCE_URLS["reports"]
    if _is_compliance_query(q):
        return TOPIC_SOURCE_URLS["mutual_funds_overview"]
    return None


def _is_out_of_scope(query: str) -> bool:
    """Queries about fixed deposits, share/stock price, or non-MF topics are out of scope."""
    q = _normalize(query)
    out_of_scope_phrases = (
        "fixed deposit",
        " fd ",
        "share price",
        "stock price",
        "hdfc bank",
    )
    return any(p in q for p in out_of_scope_phrases)


def classify(user_message: str) -> ClassificationResult:
    if not user_message or not user_message.strip():
        return ClassificationResult(
            intent_type=IntentType.OUT_OF_SCOPE,
            requested_attributes=[],
            scheme_candidate=None,
            source_url_hint=None,
            confidence=0.0,
        )

    if _is_out_of_scope(user_message):
        return ClassificationResult(
            intent_type=IntentType.OUT_OF_SCOPE,
            requested_attributes=[],
            scheme_candidate=None,
            source_url_hint=TOPIC_SOURCE_URLS["mutual_funds_overview"],
            confidence=0.95,
        )

    if _detect_advice_or_opinion(user_message):
        scheme = _resolve_scheme_slug(user_message)
        hint = None
        if scheme:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT underlying_url FROM mutual_fund_schemes WHERE scheme_slug = ?",
                    (scheme,),
                )
                row = cur.fetchone()
                if row:
                    hint = row[0]
            finally:
                conn.close()
        if not hint:
            hint = _topic_source_hint(user_message) or TOPIC_SOURCE_URLS[
                "mutual_funds_overview"
            ]
        return ClassificationResult(
            intent_type=IntentType.ADVICE_OR_OPINION,
            requested_attributes=[],
            scheme_candidate=scheme,
            source_url_hint=hint,
            confidence=0.95,
        )

    scheme = _resolve_scheme_slug(user_message)
    attrs = _extract_attributes(user_message)

    # Fees/definition topics without a specific scheme.
    if _is_definition_or_fees_query(user_message) and not scheme:
        hint = _topic_source_hint(user_message) or TOPIC_SOURCE_URLS["fees"]
        return ClassificationResult(
            intent_type=IntentType.GENERAL_DEFINITION
            if "what is" in _normalize(user_message)
            else IntentType.FEES_CHARGES,
            requested_attributes=[],
            scheme_candidate=None,
            source_url_hint=hint,
            confidence=0.9,
        )

    # Statement/report topics (statements, capital gains, transaction history, tax docs).
    if _is_statement_query(user_message):
        return ClassificationResult(
            intent_type=IntentType.OTHER_FACTUAL,
            requested_attributes=[],
            scheme_candidate=None,
            source_url_hint=TOPIC_SOURCE_URLS["reports"],
            confidence=0.9,
        )

    # Compliance / safety topics (guarantees, negative returns, risk-free, fixed returns).
    if _is_compliance_query(user_message):
        # If a specific scheme is mentioned, prefer its scheme page; otherwise, the MF overview page.
        hint = None
        if scheme:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT underlying_url FROM mutual_fund_schemes WHERE scheme_slug = ?",
                    (scheme,),
                )
                row = cur.fetchone()
                if row:
                    hint = row[0]
            finally:
                conn.close()
        if not hint:
            hint = TOPIC_SOURCE_URLS["mutual_funds_overview"]
        return ClassificationResult(
            intent_type=IntentType.OTHER_FACTUAL,
            requested_attributes=[],
            scheme_candidate=scheme,
            source_url_hint=hint,
            confidence=0.9,
        )

    # Scheme facts (including ELSS / tax saver).
    if scheme and (
        attrs
        or any(
            kw in _normalize(user_message)
            for kw in [
                "expense",
                "exit",
                "sip",
                "lock in",
                "lock-in",
                "risk",
                "benchmark",
                "category",
                "detail",
                "info",
            ]
        )
    ):
        return ClassificationResult(
            intent_type=IntentType.SCHEME_FACT,
            requested_attributes=attrs if attrs else list(SUPPORTED_SCHEME_ATTRIBUTES),
            scheme_candidate=scheme,
            source_url_hint=None,
            confidence=0.85,
        )

    if scheme:
        return ClassificationResult(
            intent_type=IntentType.SCHEME_FACT,
            requested_attributes=list(SUPPORTED_SCHEME_ATTRIBUTES),
            scheme_candidate=scheme,
            source_url_hint=None,
            confidence=0.8,
        )

    # Fallback: other factual question, possibly with a topic source hint.
    return ClassificationResult(
        intent_type=IntentType.OTHER_FACTUAL,
        requested_attributes=[],
        scheme_candidate=None,
        source_url_hint=_topic_source_hint(user_message),
        confidence=0.5,
    )


__all__ = ["ClassificationResult", "classify", "TOPIC_SOURCE_URLS"]

