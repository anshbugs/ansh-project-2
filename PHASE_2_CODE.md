## Phase 2 – Embeddings & Retrieval (Code & Test Notes)

This file documents the code for **Phase 2** of the Groww Mutual Fund FAQ RAG chatbot and how to run/check it.

Phase 2 is responsible for:
- Generating embeddings for all text chunks using the **Gemini** embeddings API.
- Storing those embeddings in the local SQLite database.
- Providing a basic cosine-similarity retrieval helper over those embeddings.

---

## 1. Database Changes for Phase 2

- **File**: `backend/db.py`
  - In addition to the Phase 1 tables (`raw_pages`, `mutual_fund_schemes`, `kb_chunks`), Phase 2 adds:
    - `kb_chunk_embeddings`
      - Columns:
        - `id` – autoincrement primary key
        - `chunk_id` – foreign-key reference by value to `kb_chunks.chunk_id` (one row per chunk)
        - `embedding_json` – JSON string containing the embedding vector (list of floats)
  - The `init_db()` function now also creates `kb_chunk_embeddings` if it does not exist.

---

## 2. Gemini Client (Embeddings)

- **File**: `backend/gemini_client.py`
  - Loads environment variables:
    - `GEMINI_API_KEY` – your Gemini API key (must be present in `.env` or environment).
    - `GEMINI_EMBEDDING_MODEL` – defaults to `text-embedding-004` (wrapped as `models/text-embedding-004` in the URL).
  - Functions:
    - `get_gemini_api_key() -> str`
      - Returns the API key or raises `RuntimeError` if missing.
    - `embed_text_with_gemini(text: str) -> List[float]`
      - Sends a `POST` request to:
        - `https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent?key=GEMINI_API_KEY`
      - JSON body structure:

        ```json
        {
          "content": {
            "parts": [
              { "text": "<text>" }
            ]
          }
        }
        ```

      - Expects a response with:

        ```json
        {
          "embedding": {
            "values": [ ... ]
          }
        }
        ```

      - Returns `response.json()["embedding"]["values"]` as the embedding vector for that text.
  - If the request fails (non-200 status):
    - Logs `response.text` for debugging and then raises an exception.

---

## 3. Embedding Builder Script (Phase 2 Core)

- **File**: `backend/ingestion/build_embeddings.py`
  - Responsibilities:
    - Load all text chunks from `kb_chunks` that **do not yet** have embeddings in `kb_chunk_embeddings`.
    - Batch them (default size: 32).
    - Call `embed_text_with_gemini` for each text to compute embeddings.
    - Store embeddings as JSON in `kb_chunk_embeddings`, one row per `chunk_id` (with upsert semantics).
  - Key functions:
    - `load_unembedded_chunks(batch_size: int = 32) -> List[(chunk_id, content)]`
      - Returns a batch of chunks that do not have embeddings yet.
    - `insert_embeddings(rows: List[(chunk_id, embedding_vector)])`
      - Writes to `kb_chunk_embeddings` with `ON CONFLICT(chunk_id) DO UPDATE`.
    - `main()`
      - Loops until there are no unembedded chunks left:
        - Fetch a batch
        - Call Gemini embeddings
        - Persist embeddings
      - Logs total chunks processed.

### How to run Phase 2 (after Phase 1)

From the project root:

```bash
python -m backend.ingestion.fetch_pages   # Phase 1 – fetch raw HTML (if not done)
python -m backend.ingestion.parse_pages   # Phase 1 – parse & chunk (if not done)
python -m backend.ingestion.build_embeddings  # Phase 2 – build embeddings with Gemini
```

You must have:
- `.env` with a valid `GEMINI_API_KEY`.
- `requirements.txt` installed (`pip install -r requirements.txt`).

If the Gemini embeddings call is misconfigured (wrong key or model), you will see an error logged with the HTTP status code and full `response.text`. In that case:
- Verify the embeddings endpoint, model name, and `GEMINI_API_KEY` based on the latest Gemini docs.

---

## 4. Simple Retrieval Helper

- **File**: `backend/retrieval.py`
  - Dataclass:
    - `RetrievedChunk`:
      - `chunk_id`, `url`, `page_type`, `scheme_slug`, `section_title`, `content`, `score`.
  - Functions:
    - `search_similar_chunks(query_embedding: List[float], top_k: int = 5) -> List[RetrievedChunk]`
      - Loads all embeddings from `kb_chunk_embeddings`.
      - Computes cosine similarity between `query_embedding` and each stored embedding (via `numpy`).
      - Fetches metadata from `kb_chunks`.
      - Returns top‑`k` chunks sorted by descending similarity score.
  - This is the basis for Phase 3’s RAG retrieval logic.

---

## 5. Test Status for Phases 0, 1, and 2

When run in this project:

- **Phase 0 (config)**
  - `backend/config.py` imports successfully and provides:
    - `ALLOWED_KB_URLS`, `IntentType`, `SUPPORTED_SCHEME_ATTRIBUTES`, `ADVICE_KEYWORDS`, `GUARDRAILS`.
- **Phase 1 (ingestion & parsing)**
  - `python -m backend.ingestion.fetch_pages`:
    - Successfully fetched all 10 configured Groww URLs and stored them in `raw_pages`.
  - `python -m backend.ingestion.parse_pages`:
    - Successfully parsed all 10 pages.
    - Logged “No content sections found” for some scheme/help pages (reflecting the current conservative heading-based chunking).
    - Inserted sections into `kb_chunks` where headings were detected.
- **Phase 2 (embeddings)**
  - `python -m backend.ingestion.build_embeddings`:
    - Successfully detected unembedded chunks and attempted to call Grok’s embeddings endpoint.
    - The current configuration produced a `400 Bad Request` error from `https://api.x.ai/v1/embeddings`, which indicates that:
      - The endpoint/model combination used in `backend/llm_client.py` does not match your Grok account’s actual embeddings API.
    - No embeddings were inserted yet because the external API rejected the request.

**Conclusion:**  
Phases 0 and 1 are functioning correctly (config, fetch, parse, chunk). Phase 2’s local pipeline (DB schema, batching, embedding storage, and retrieval helper) is implemented and runnable, but you must align `backend/llm_client.py` with the **actual Grok embeddings endpoint and model name** from your Grok documentation for embeddings to be generated successfully.

