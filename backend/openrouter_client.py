from __future__ import annotations

"""
OpenRouter client for embeddings (Phase 2) and chat (Phase 3).

API keys and URL/model come from backend.config (get_env):
- Local: .env
- Streamlit Cloud: st.secrets

Required OpenRouter headers are sent on every request to avoid 401.
"""

import logging
from typing import List, Optional

import requests

from backend.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_CHAT_MODEL,
)

logger = logging.getLogger(__name__)

# Embeddings model (local sentence-transformers used in practice; this is fallback if OpenRouter embeddings were used)
OPENROUTER_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_openrouter_api_key() -> str:
    """Return the OpenRouter API key from config; raise if missing or empty."""
    if not OPENROUTER_API_KEY or not str(OPENROUTER_API_KEY).strip():
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Add it to .env (local) or Streamlit Secrets (OPENROUTER_API_KEY) when deployed."
        )
    return str(OPENROUTER_API_KEY).strip()


def _openrouter_headers() -> dict:
    """Required OpenRouter headers for hosted apps (e.g. Streamlit Cloud); missing them can cause 401."""
    api_key = get_openrouter_api_key()
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": "Groww-Mutual-Fund-Assistant",
    }


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch-embed a list of texts via OpenRouter /embeddings."""
    if not texts:
        return []
    url = f"{OPENROUTER_BASE_URL}/embeddings"
    headers = _openrouter_headers()
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
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = _openrouter_headers()

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

