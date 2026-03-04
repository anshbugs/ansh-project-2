## Phase 5 – Backend Modules & APIs (Implementation Overview)

Phase 5 packages the RAG pipeline behind a clean HTTP API so the React chatbot (or any client) can interact with the system.

---

## 1. Module Layout

- `backend/config.py` – Scope, guardrails, allowed URLs, intent types.
- `backend/db.py` – SQLite storage (`raw_pages`, `mutual_fund_schemes`, `kb_chunks`, `kb_chunk_embeddings`).
- `backend/ingestion/` – Phase 1 & 2 scripts:
  - `fetch_pages.py`, `parse_pages.py`, `build_embeddings.py`.
- `backend/retrieval.py` – Vector retrieval (`search_similar_chunks`).
- `backend/intent_classifier.py` – Rule-based intent classification.
- `backend/retriever.py` – Hybrid retrieval service by intent (structured + RAG chunks).
- `backend/openrouter_client.py` – LLM and embedding client (OpenRouter).
- `backend/rag_orchestrator.py` – RAG pipeline orchestration (classify → retrieve → generate).
- `backend/app.py` – FastAPI app exposing `/api/chat` and `/api/health`.

---

## 2. FastAPI App (`backend/app.py`)

### 2.1 App setup

```python
app = FastAPI(title="Groww MF FAQ Chat API", version="0.1.0")
```

### 2.2 Models

- `ChatMessage`:
  - `role`: `"user"` or `"assistant"`.
  - `content`: string.
- `ChatRequest`:
  - `session_id`: optional string.
  - `messages`: list of `ChatMessage`.
- `ChatResponseModel`:
  - `answer`: string.
  - `source_url`: string (one of the allowed Groww URLs).
  - `intent_type`: enum value as string.
  - `scheme_slug`: optional scheme slug.
  - `refusal`: boolean.

### 2.3 Endpoints

- `GET /api/health`
  - Returns `{"status": "ok"}`.

- `POST /api/chat`
  - Validates that:
    - `messages` is non-empty.
    - The last message is from `"user"`.
  - Calls:

    ```python
    resp: ChatResponse = chat(last.content)
    ```

    where `chat` is from `backend.rag_orchestrator`.
  - On success:
    - Returns `ChatResponseModel` populated from `ChatResponse`.
  - On error:
    - If the error string looks like a rate-limit/429:
      - Returns **503** with `"API rate limit exceeded (Grok/Gemini). Please try again in a minute."`
    - Otherwise:
      - Returns **500** with the error message.

---

## 3. RAG Orchestration (`backend/rag_orchestrator.py`)

- Exposes `chat(user_message: str, _history: Optional[List[dict]] = None) -> ChatResponse`.
- Uses:
  - `intent_classifier.classify` to understand the query.
  - `retriever.retrieve` to get structured facts, chunks, and a `source_url`.
  - `openrouter_client.generate_content` to:
    - Generate refusal messages for advice/opinion or out-of-scope.
    - Generate factual answers when context is available.
- Ensures:
  - A single, clear `Source: <Groww URL>` is appended to each non-refusal answer.
  - No investment advice is provided.

---

## 4. How to Run the Backend API

From the project root:

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Then:

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is expense ratio?"}]}'
```

This completes Phase 5 by documenting and confirming the backend API surface over the previously implemented ingestion, retrieval, and RAG layers.

