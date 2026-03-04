from __future__ import annotations

"""
Gemini embeddings client for Phase 2.

Uses the public Gemini embeddings REST API:
- Endpoint:
    POST https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=GEMINI_API_KEY
- JSON body:
    {
      "content": {
        "parts": [
          { "text": "<text>" }
        ]
      }
    }

Response shape (simplified):
    { "embedding": { "values": [ ... ] } }
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

# Load .env from project root so key is found when run as python -m backend.ingestion.build_embeddings
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = _PROJECT_ROOT / ".env"
load_dotenv(_env_path, override=True)
logger = logging.getLogger(__name__)
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Loading .env from %s; GEMINI_API_KEY present: %s", _env_path, bool(os.getenv("GEMINI_API_KEY")))

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Please add it to your environment or .env file."
        )
    return api_key


def embed_text_with_gemini(text: str) -> List[float]:
    """
    Generate an embedding for a single text using the Gemini embeddings endpoint.

    Returns:
        A list of floats corresponding to response.json()["embedding"]["values"].
    """
    api_key = get_gemini_api_key()
    model = GEMINI_EMBEDDING_MODEL
    url = f"{GEMINI_API_BASE_URL}/models/{model}:embedContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "content": {
            "parts": [
                {"text": text},
            ]
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        logger.error(
            "Gemini embeddings request failed with status %s: %s",
            resp.status_code,
            resp.text,
        )
        resp.raise_for_status()

    data = resp.json()
    try:
        values = data["embedding"]["values"]
    except (KeyError, TypeError) as exc:  # noqa: BLE001
        logger.error("Unexpected Gemini embeddings response format: %s", data)
        raise RuntimeError("Unexpected Gemini embeddings response format") from exc
    return values


GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")


def generate_content(
    user_text: str,
    system_instruction: Optional[str] = None,
    context_text: Optional[str] = None,
) -> str:
    """
    Call Gemini generateContent to produce a single turn reply.
    If context_text is provided, it is prepended to the user message for RAG.
    """
    api_key = get_gemini_api_key()
    url = f"{GEMINI_API_BASE_URL}/models/{GEMINI_CHAT_MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    parts = []
    if context_text:
        parts.append({"text": f"Context from Groww pages:\n{context_text}\n\nUser question: {user_text}"})
    else:
        parts.append({"text": user_text})

    payload = {"contents": [{"parts": parts}]}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        logger.error("Gemini generateContent failed with status %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()

    data = resp.json()
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return "I couldn't generate a response."
        parts_out = candidates[0].get("content", {}).get("parts", [])
        if not parts_out:
            return "I couldn't generate a response."
        return parts_out[0].get("text", "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected generateContent response: %s", data)
        raise RuntimeError("Unexpected generateContent response") from exc


__all__ = [
    "embed_text_with_gemini",
    "get_gemini_api_key",
    "generate_content",
    "GEMINI_API_BASE_URL",
    "GEMINI_EMBEDDING_MODEL",
    "GEMINI_CHAT_MODEL",
]

