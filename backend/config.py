from __future__ import annotations

"""
Phase 0 – Scope & Guardrails configuration.

This module centralises:
- Allowed Groww URLs that form the knowledge base.
- High-level intent categories.
- Phrases that indicate advice/opinion queries which must be refused.
- Supported factual attribute types for scheme queries.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Set


# Allowed Groww URLs used for ingestion (Phase 1) and as canonical sources.
ALLOWED_KB_URLS: List[str] = [
    # Scheme pages
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-arbitrage-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-value-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-tax-saver-fund-direct-growth",
    # AMC page
    "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
    # Educational / help / overview pages
    "https://groww.in/p/expense-ratio",
    "https://groww.in/p/exit-load-in-mutual-funds",
    "https://groww.in/help/mutual-funds/order/what-are-the-charges-applicable-for-redeeming--53",
    "https://groww.in/help/mutual-funds/reports",
    "https://groww.in/p/mutual-funds",
]


class IntentType(str, Enum):
    """High-level intent categories used throughout the backend."""

    SCHEME_FACT = "SCHEME_FACT"
    GENERAL_DEFINITION = "GENERAL_DEFINITION"
    FEES_CHARGES = "FEES_CHARGES"
    OTHER_FACTUAL = "OTHER_FACTUAL"
    ADVICE_OR_OPINION = "ADVICE_OR_OPINION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


SUPPORTED_SCHEME_ATTRIBUTES: Set[str] = {
    "expense_ratio",
    "exit_load",
    "min_sip_amount",
    "min_lumpsum_amount",
    "risk_level",
    "benchmark_index",
    "category",
    "amc_name",
}


ADVICE_KEYWORDS: Set[str] = {
    "should i invest",
    "should i buy",
    "is this a good fund",
    "is this fund good",
    "good for long term",
    "long term investment",
    "which is better",
    "better than",
    "highest returns",
    "safe or risky",
    "safe or not",
    "is it safe",
    "high return",
    "best fund",
    "recommend",
    "recommendation",
    "should i redeem",
    "redeem my mutual fund",
    "which fund should i buy",
    "which fund should i buy in 2025",
}


@dataclass(frozen=True)
class GuardrailConfig:
    """
    Guardrail settings used by the backend.

    These values are referenced when classifying queries and enforcing
    non-advisory behaviour in later phases.
    """

    allowed_kb_urls: List[str]
    advice_keywords: Set[str]
    supported_scheme_attributes: Set[str]


GUARDRAILS = GuardrailConfig(
    allowed_kb_urls=ALLOWED_KB_URLS,
    advice_keywords=ADVICE_KEYWORDS,
    supported_scheme_attributes=SUPPORTED_SCHEME_ATTRIBUTES,
)


__all__ = [
    "ALLOWED_KB_URLS",
    "IntentType",
    "SUPPORTED_SCHEME_ATTRIBUTES",
    "ADVICE_KEYWORDS",
    "GUARDRAILS",
]

