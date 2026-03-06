from __future__ import annotations

"""
Phase 3 – FastAPI app: POST /api/chat and GET /api/health.
"""

from typing import List, Optional

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag_orchestrator import chat, ChatResponse


app = FastAPI(title="Groww MF FAQ Chat API", version="0.1.0")

def _cors_allow_origins() -> list[str]:
    """
    Configure CORS origins.

    - Local default: allow Vite on common ports
    - Production: set CORS_ALLOW_ORIGINS to a comma-separated list of origins
      (e.g. "https://your-frontend.vercel.app,https://www.yourdomain.com")
    - If CORS_ALLOW_ORIGINS is "*", allow all origins (credentials will be disabled)
    """
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    if raw == "*":
        return ["*"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


_allow_origins = _cors_allow_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=("*" not in _allow_origins),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    messages: List[ChatMessage]


class ChatResponseModel(BaseModel):
    answer: str
    source_url: str
    intent_type: str
    scheme_slug: Optional[str] = None
    refusal: bool


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "message": "Groww MF FAQ Chat API",
        "docs": "/docs",
        "health": "/api/health",
        "chat": "POST /api/chat",
        "hint": "For the chat UI, run the frontend (npm run dev in frontend/) and open http://localhost:5173",
    }


@app.post("/api/chat", response_model=ChatResponseModel)
def api_chat(body: ChatRequest):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages required")
    last = body.messages[-1]
    if last.role != "user":
        raise HTTPException(status_code=400, detail="last message must be from user")
    try:
        resp: ChatResponse = chat(last.content)
        return ChatResponseModel(
            answer=resp.answer,
            source_url=resp.source_url,
            intent_type=resp.intent_type,
            scheme_slug=resp.scheme_slug,
            refusal=resp.refusal,
        )
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Too Many Requests" in err_str:
            raise HTTPException(
                status_code=503,
                detail="API rate limit exceeded (Grok/Gemini). Please try again in a minute.",
            ) from e
        raise HTTPException(status_code=500, detail=err_str) from e
