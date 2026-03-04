## Phase 4 – LLM Answer Generation (Code & Test Notes)

Phase 4 takes the retrieved context (structured facts + chunks) and generates a concise, guarded answer with a single Groww source URL, using the LLM via OpenRouter.

---

## 1. LLM Client (OpenRouter)

**File:** `backend/openrouter_client.py`

- **Environment variables**
  - `OPENROUTER_API_KEY` – your OpenRouter key (**required**).
  - `OPENROUTER_BASE_URL` – defaults to `https://openrouter.ai/api/v1`.
  - `OPENROUTER_CHAT_MODEL` – chat model ID; must be a valid OpenRouter model.
  - `OPENROUTER_EMBED_MODEL` – embedding model ID (used in Phase 2/3).

- **Function:** `generate_content(user_text, system_instruction=None, context_text=None) -> str`
  - Builds a `messages` array:
    - Optional `system` message (Phase 4 system or refusal prompt).
    - `user` message containing either:
      - Just `user_text`, or
      - `Context from Groww pages:\n<context_text>\n\nUser question: <user_text>` when context is available.
  - Sends:

    ```json
    POST /chat/completions
    {
      "model": "<OPENROUTER_CHAT_MODEL>",
      "messages": [...],
      "stream": false
    }
    ```

  - Returns the first choice’s `message.content`, or a fallback string if no choices.

---

## 2. RAG Orchestrator (Classification → Retrieval → Generation)

**File:** `backend/rag_orchestrator.py`

- **System prompts**
  - `SYSTEM_PROMPT`:
    - Enforces factual answers, Groww-only context, no advice, 2–5 sentence answers, no invented URLs.
  - `REFUSAL_PROMPT`:
    - For advice/opinion queries: politely refuses to give recommendations; may point to factual Groww info.

- **Data model**
  - `ChatResponse` dataclass:
    - `answer: str`
    - `source_url: str`
    - `intent_type: str`
    - `scheme_slug: Optional[str]`
    - `refusal: bool`

- **Pipeline:** `chat(user_message: str, _history: Optional[List[dict]] = None) -> ChatResponse`
  1. **Classify**
     - Uses `intent_classifier.classify` to get `intent_type`, `scheme_candidate`, etc.
  2. **Retrieve**
     - Uses `retriever.retrieve` to get:
       - `structured_facts` (scheme facts string).
       - `chunks` (top-k retrieved text chunks).
       - `source_url` (chosen Groww URL).
       - `refusal` flag (for advice/out-of-scope).
  3. **Refusal handling**
     - If `retrieval.refusal` is True:
       - For `ADVICE_OR_OPINION`: calls `generate_content` with `REFUSAL_PROMPT`.
       - For `OUT_OF_SCOPE`: returns a fixed explanatory message.
       - Always returns `ChatResponse` with `refusal=True` and `source_url` set.
  4. **Context build**
     - `_build_context(retrieval)`:
       - Concatenates `structured_facts` + up to 5 chunks:

         ```text
         [Section Title]
         chunk content
         ```

  5. **Answer generation**
     - If no context → fixed “don’t have enough information” message.
     - Else → calls `generate_content(user_message, system_instruction=SYSTEM_PROMPT, context_text=context)`.
  6. **Citation enforcement**
     - If the generated answer does not already end with the `source_url`, appends:

       ```text
       Source: <source_url>
       ```

  7. Returns `ChatResponse` with:
     - `answer` (LLM output + citation)
     - `source_url` (single Groww URL)
     - `intent_type`, `scheme_slug`, `refusal=False`.

---

## 3. API Layer

**File:** `backend/app.py`

- `GET /api/health`:
  - Returns `{"status": "ok"}`.
- `POST /api/chat`:
  - Expects:

    ```json
    {
      "session_id": "optional",
      "messages": [
        { "role": "user", "content": "..." },
        ...
      ]
    }
    ```

  - Uses the **last** user message as `user_message`.
  - Calls `rag_orchestrator.chat`.
  - On success: returns `answer`, `source_url`, `intent_type`, `scheme_slug`, `refusal`.
  - On rate-limit errors (429 / “Too Many Requests”): returns **503** with a clear message.
  - On other exceptions: returns **500** with error details.

---

## 4. How to Run & Test Phase 4

1. **Ensure embeddings exist (Phase 2)**

   ```bash
   python -m backend.ingestion.fetch_pages
   python -m backend.ingestion.parse_pages
   python -m backend.ingestion.build_embeddings
   ```

2. **Start the API**

   ```bash
   uvicorn backend.app:app --host 127.0.0.1 --port 8000
   ```

3. **Health check**

   ```bash
   curl http://127.0.0.1:8000/api/health
   ```

4. **Chat call**

   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"What is expense ratio?"}]}'
   ```

   - With a valid `OPENROUTER_CHAT_MODEL` and enough quota, the response will be:
     - A concise factual answer.
     - A single `source_url` pointing to one of the allowed Groww pages (e.g. `https://groww.in/p/expense-ratio`).

This file documents the Phase 4 implementation (LLM answer generation) and how it connects to the earlier phases and the FastAPI backend.

