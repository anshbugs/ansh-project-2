# Phase 3 – Query Understanding & Retrieval Flow (Code & Test)

Phase 3 implements the backend API and RAG pipeline: intent classification → hybrid retrieval → Gemini answer generation → single source URL.

## 1. Intent classifier

**File:** `backend/intent_classifier.py`

- **classify(user_message: str) -> ClassificationResult**
  - Rule-based intent detection using:
    - `ADVICE_KEYWORDS` from config → `ADVICE_OR_OPINION`
    - `SCHEME_KEYWORDS` + DB lookup → `scheme_candidate` slug
    - `ATTRIBUTE_KEYWORDS` → `requested_attributes`
    - Definition/fees phrases → `GENERAL_DEFINITION` / `FEES_CHARGES` with `source_url_hint`
  - Returns: `intent_type`, `requested_attributes`, `scheme_candidate`, `source_url_hint`, `confidence`

## 2. Filtered retrieval

**File:** `backend/retrieval.py`

- **search_similar_chunks(query_embedding, top_k=5, page_types=None, scheme_slug=None)**
  - Optional filters: `page_types` (e.g. `["definition","blog","help"]`), `scheme_slug`
  - Returns top-k `RetrievedChunk` with metadata and score

## 3. Retriever (hybrid by intent)

**File:** `backend/retriever.py`

- **retrieve(user_message, classification, top_k=5) -> RetrievalResult**
  - `ADVICE_OR_OPINION` / `OUT_OF_SCOPE` → refusal=True, single `source_url`
  - `SCHEME_FACT` → structured row from `mutual_fund_schemes` + vector search (optionally filtered by `scheme_slug`)
  - `GENERAL_DEFINITION` / `FEES_CHARGES` → vector search with `page_types=["definition","blog","help"]`, `source_url` from classifier hint
  - Returns: `structured_facts`, `chunks`, `source_url`, `refusal`

## 4. Gemini generateContent

**File:** `backend/gemini_client.py`

- **generate_content(user_text, system_instruction=None, context_text=None) -> str**
  - Calls `POST .../models/{GEMINI_CHAT_MODEL}:generateContent` (default `gemini-2.0-flash`)
  - Uses `context_text` for RAG; returns generated text

## 5. RAG orchestrator

**File:** `backend/rag_orchestrator.py`

- **chat(user_message, _history=None) -> ChatResponse**
  - Runs: classify → retrieve → if refusal: generate refusal reply with Gemini or fixed message; else build context from structured_facts + chunks → generate_content → append `Source: {source_url}`
  - Returns: `answer`, `source_url`, `intent_type`, `scheme_slug`, `refusal`

## 6. FastAPI app

**File:** `backend/app.py`

- **GET /api/health** → `{"status": "ok"}`
- **POST /api/chat**
  - Body: `{ "session_id": optional, "messages": [ { "role": "user"|"assistant", "content": "..." } ] }`
  - Uses last user message; returns `answer`, `source_url`, `intent_type`, `scheme_slug`, `refusal`
  - On Gemini 429: returns **503** with message "Gemini API rate limit exceeded. Please try again in a minute."

## How to run and test

```bash
# Install
pip install -r requirements.txt

# Run API
uvicorn backend.app:app --host 127.0.0.1 --port 8000

# Test health
curl http://127.0.0.1:8000/api/health

# Test chat
curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"messages\":[{\"role\":\"user\",\"content\":\"What is expense ratio?\"}]}"
```

Or with FastAPI TestClient (no server):

```python
from fastapi.testclient import TestClient
from backend.app import app
client = TestClient(app)
client.get("/api/health")  # 200
client.post("/api/chat", json={"messages": [{"role": "user", "content": "What is expense ratio?"}]})
```

## Test status

- **Intent classifier:** "What is expense ratio?" → GENERAL_DEFINITION; "HDFC mid cap expense ratio?" → SCHEME_FACT + scheme_candidate; "Should I invest?" → ADVICE_OR_OPINION.
- **GET /api/health:** 200, `{"status":"ok"}`.
- **POST /api/chat:** Full pipeline runs; when Gemini quota is exceeded, API returns 503 with a clear message instead of 500.
