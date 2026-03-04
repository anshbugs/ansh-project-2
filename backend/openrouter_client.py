from __future__ import annotations

"""
OpenRouter client for embeddings (Phase 2) and chat (Phase 3).

Uses env vars from .env:
- OPENROUTER_API_KEY
- OPENROUTER_BASE_URL (default: https://openrouter.ai/api/v1)
- OPENROUTER_EMBED_MODEL (e.g. sentence-transformers/all-MiniLM-L6-v2)
- OPENROUTER_CHAT_MODEL (e.g. mistralai/mistral-7b-instruct:free)
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

logger = logging.getLogger(__name__)

OPENROUTER_API_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_EMBED_MODEL = os.getenv("OPENROUTER_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENROUTER_CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "mistralai/mistral-7b-instruct")


def get_openrouter_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")
    return api_key


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch-embed a list of texts via OpenRouter /embeddings."""
    if not texts:
        return []
    api_key = get_openrouter_api_key()
    url = f"{OPENROUTER_API_BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_EMBED_MODEL,
        "input": texts,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        logger.error("OpenRouter embeddings failed %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    data = resp.json()
    try:
        items = data["data"]
        embs = [item["embedding"] for item in items]
    except (KeyError, TypeError) as exc:  # noqa: BLE001
        logger.error("Unexpected OpenRouter embeddings response: %s", data)
        raise RuntimeError("Unexpected OpenRouter embeddings response") from exc
    if len(embs) != len(texts):
        raise RuntimeError("Mismatch between inputs and embeddings from OpenRouter")
    return embs


def embed_text(text: str) -> List[float]:
    """Embed a single text using embed_texts."""
    embs = embed_texts([text])
    return embs[0]


def generate_content(
    user_text: str,
    system_instruction: Optional[str] = None,
    context_text: Optional[str] = None,
) -> str:
    """Call OpenRouter chat/completions to produce a single reply."""
    api_key = get_openrouter_api_key()
    url = f"{OPENROUTER_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    content = user_text
    if context_text:
        content = f"Context from Groww pages:\n{context_text}\n\nUser question: {user_text}"

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": content})

    payload = {
        "model": OPENROUTER_CHAT_MODEL,
        "messages": messages,
        "stream": False,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        logger.error("OpenRouter chat failed %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    data = resp.json()
    try:
        choices = data.get("choices", [])
        if not choices:
            return "I couldn't generate a response."
        return (choices[0].get("message", {}).get("content") or "").strip()
    except (KeyError, TypeError) as exc:  # noqa: BLE001
        logger.error("Unexpected OpenRouter chat response: %s", data)
        raise RuntimeError("Unexpected OpenRouter chat response") from exc


__all__ = [
    "embed_texts",
    "embed_text",
    "generate_content",
    "get_openrouter_api_key",
]

