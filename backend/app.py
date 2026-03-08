from __future__ import annotations

"""
Phase 3 – FastAPI app: POST /api/chat and GET /api/health.

When STATIC_DIR is set (e.g. in Docker), also serves the built frontend SPA.
"""

import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.rag_orchestrator import chat, ChatResponse


app = FastAPI(title="Groww MF FAQ Chat API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    static_dir = os.environ.get("STATIC_DIR")
    if static_dir:
        index_path = Path(static_dir) / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
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
        answer = (resp.answer or "").strip() or "No answer was generated. Please try again."
        return ChatResponseModel(
            answer=answer,
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


# Serve built frontend when STATIC_DIR is set (e.g. Docker / Fly.io)
_static_dir = os.environ.get("STATIC_DIR")
if _static_dir:
    _static_path = Path(_static_dir)
    _assets = _static_path / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        if path.startswith("api/") or path in ("docs", "openapi.json", "redoc") or path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = _static_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not found")
