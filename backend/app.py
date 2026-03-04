from __future__ import annotations

"""
Phase 3 – FastAPI app: POST /api/chat and GET /api/health.
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.rag_orchestrator import chat, ChatResponse


app = FastAPI(title="Groww MF FAQ Chat API", version="0.1.0")


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
