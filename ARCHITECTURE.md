## Groww Mutual Fund FAQ RAG Chatbot – Architecture

This document describes the phase-wise architecture for a Retrieval-Augmented Generation (RAG) chatbot that answers factual questions about specific HDFC mutual fund schemes using only selected public Groww pages. Deployment is out of scope for now; the focus is on a working prototype architecture.

Allowed knowledge sources:
- `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth`
- `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth`
- `https://groww.in/mutual-funds/hdfc-arbitrage-fund-direct-growth`
- `https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth`
- `https://groww.in/mutual-funds/hdfc-value-fund-direct-plan-growth`
- `https://groww.in/mutual-funds/amc/hdfc-mutual-funds`
- `https://groww.in/p/expense-ratio`
- `https://groww.in/p/exit-load-in-mutual-funds`
- `https://groww.in/blog/mutual-fund-fees-and-charges`
- `https://groww.in/help/mutual-funds/order/what-are-the-charges-applicable-for-redeeming--53`

The chatbot:
- Answers only **factual** questions about these schemes and fee/definition topics.
- Must always include **exactly one** source link (one of the above URLs) in every answer.
- Must **not** provide investment advice, opinions, predictions, or recommendations.

---

## Phase 0 – Scope & Guardrails

- **Supported questions**
  - Scheme-specific facts: expense ratio, exit load, minimum SIP amount, minimum lump sum, risk level / riskometer, benchmark index, category, AMC details, etc.
  - General definitions: what is expense ratio, what is exit load, what mutual fund fees and charges mean, and Groww help content on charges.
- **Forbidden**
  - “Should I invest?”, “Is this a good fund?”, “Which is better?”, “Will this give good returns?”, or any recommendation/comparison.
- **Guardrail rules**
  - Use **only** content retrieved from the allowed Groww URLs.
  - If the answer is not present in the retrieved context, say you do not know, do not guess.
  - If the question is advice/opinion based, politely refuse and optionally provide factual info plus a clear disclaimer.
  - Every answer must contain exactly one source URL.

---

## Phase 1 – Data Ingestion & Parsing

### 1.1 Tech Stack for Ingestion

- **Language**: Python
- **Libraries**
  - `requests` / `httpx` for HTTP fetching.
  - `beautifulsoup4` and optionally `lxml` / `readability-lxml` for HTML parsing and main-content extraction.
  - `pydantic` for typed models.
- **Storage for prototype**
  - PostgreSQL (for structured facts and raw/parsed content).
  - `pgvector` extension or a vector database (e.g., Qdrant) for embeddings.

### 1.2 Raw Page Fetcher

- Input: the static list of Groww URLs.
- Responsibilities:
  - Fetch HTML for each URL (with appropriate headers and robots.txt respect).
  - Store results in a `raw_pages` table:
    - `id`
    - `url`
    - `html`
    - `status_code`
    - `fetched_at`
    - Optional `etag` / `last_modified` for future incremental refresh.

### 1.3 Parsing to Structured & Unstructured Data

Split content into:

- **Structured scheme attributes** (for precision):
  - From each HDFC scheme page: expense ratio, exit load, min SIP, min lump sum, risk level, benchmark, category, AMC name, etc.
  - Store in `mutual_fund_schemes` table:
    - `id` (UUID)
    - `scheme_name`
    - `scheme_slug` (e.g. `hdfc-mid-cap-fund-direct-growth`)
    - `amc_name`
    - `expense_ratio`
    - `exit_load`
    - `min_sip_amount`
    - `min_lumpsum_amount`
    - `risk_level`
    - `benchmark_index`
    - `category`
    - `plan_type` (Direct / Growth)
    - `underlying_url` (Groww URL)
    - `as_of_date` (if available)
    - `last_parsed_at`

- **Unstructured explanatory text**:
  - Article bodies from the definition/help/blog URLs.
  - Narrative sections from scheme and AMC pages (investment objective, overview, etc.).
  - Cleaned to remove navigation, footer, and unrelated UI elements.

### 1.4 Chunking Strategy

- **For definitions/articles**:
  - Chunk by headings (e.g. `h2`, `h3`), preserving each logical section.
  - If a section is long, further split into ~200–400-token chunks with ~50-token overlap.

- **For scheme pages**:
  - Create small, labeled chunks for key-value sections:
    - One chunk per attribute group (e.g., “Expense ratio”, “Exit load”, “Minimum SIP”).

- **Chunk metadata** (`kb_chunks` table):
  - `chunk_id`
  - `url`
  - `page_type` (`scheme`, `definition`, `blog`, `help`, `amc`)
  - `scheme_slug` (nullable, present for scheme-specific chunks)
  - `section_title`
  - `content` (plain text)
  - `token_count`
  - `last_parsed_at`

---

## Phase 2 – Embedding & Retrieval Index

### 2.1 Embeddings

- Use an embedding model provided by **Gemini** (for example, a Gemini text-embedding model exposed via the Gemini API).
- For each chunk in `kb_chunks`:
  - Compute an embedding vector over `content`.
  - Store in `kb_chunk_embeddings` or directly in a vector DB:
    - `chunk_id`
    - `embedding` (vector)
    - Auxiliary metadata for filters (page type, scheme slug, section title).

### 2.2 Hybrid Knowledge Access

- **Structured lookup** (PostgreSQL) for:
  - Direct attributes like expense ratio, exit load, minimum SIP, risk level, benchmark, etc.
  - Provides exact values taken from the Groww pages.

- **Vector-based RAG retrieval** for:
  - Definitions and conceptual queries.
  - Narrative or descriptive scheme questions (e.g. investment objective).

This hybrid design improves accuracy on numeric/tabular fields while still allowing flexible natural-language Q&A.

---

## Phase 3 – Query Understanding & Retrieval Flow

### 3.1 Backend Stack

- **Language**: Python
- **Framework**: FastAPI for HTTP APIs.
- **Core endpoint**: `POST /api/chat`
  - Request:
    - `session_id` (string)
    - `messages`: array of `{ role: "user" | "assistant", content: string }`
  - Response:
    - `answer` (string)
    - `source_url` (string, one of the allowed URLs)
    - `intent_type` (enum)
    - `scheme_slug` (optional)
    - `refusal` (boolean)

### 3.2 Intent Classification & Entity Extraction

- Implement a lightweight classifier (rules + optionally a **Gemini** chat/completions API call) that outputs:
  - `intent_type`:
    - `SCHEME_FACT`
    - `GENERAL_DEFINITION`
    - `FEES_CHARGES`
    - `OTHER_FACTUAL`
    - `ADVICE_OR_OPINION`
    - `OUT_OF_SCOPE`
  - `requested_attributes`: e.g. `["expense_ratio"]`, `["exit_load"]`, `["min_sip"]`, `["risk_level"]`, `["benchmark"]`.
  - `scheme_candidate`: best-guess scheme slug from the query (string matching / lookup).
  - Confidence scores for routing decisions.

- Rule examples:
  - Keywords: “expense ratio”, “exit load”, “SIP”, “minimum investment”, “riskometer”, “benchmark”.
  - Advice markers: “should I invest”, “good fund”, “which is better”, “safe or risky”.

### 3.3 Retrieval Paths by Intent

#### 3.3.1 Scheme Facts (`SCHEME_FACT`)

1. Resolve scheme:
   - Map the user’s fund name/partial name to a `scheme_slug` via lookup in `mutual_fund_schemes`.
   - If multiple matches, ask for clarification.
2. Structured DB lookup:
   - Pull requested attributes from `mutual_fund_schemes`.
   - Use the scheme’s `underlying_url` as the canonical `source_url`.
3. Optional RAG enrichment:
   - For explanation-style questions, also run vector search:
     - Query = user text + scheme name.
     - Filter by `scheme_slug` or `page_type`.
   - Pass retrieved chunks to the LLM with the structured fields for a richer natural-language answer.

#### 3.3.2 Definitions & Fees (`GENERAL_DEFINITION`, `FEES_CHARGES`)

1. Vector search:
   - Query: user question.
   - Filters: `page_type IN ("definition", "blog", "help")`.
   - Retrieve top-k chunks (e.g. 3).
2. Source selection:
   - Choose a canonical page per topic, for example:
     - Expense ratio → `https://groww.in/p/expense-ratio`
     - Exit load → `https://groww.in/p/exit-load-in-mutual-funds`
     - Fees & charges → `https://groww.in/blog/mutual-fund-fees-and-charges`
     - Redeeming charges → the Groww help URL.
   - Use that as the single `source_url`.

#### 3.3.3 Advice / Opinion (`ADVICE_OR_OPINION`)

- Do not answer using RAG in a way that implies advice or recommendations.
- Generate a response that:
  - Clearly states the assistant cannot give investment advice or opinions.
  - May provide factual scheme info (via structured lookup/RAG) with a strong disclaimer.
- Use:
  - Scheme page URL if a fund is mentioned.
  - A relevant definition/fees URL otherwise.

#### 3.3.4 Out of Scope (`OUT_OF_SCOPE`)

- Politely indicate that the question is outside the assistant’s scope.
- Optionally provide a related Groww URL if any is relevant.

---

## Phase 4 – LLM Answer Generation

### 4.1 Prompting Strategy (using Gemini LLM)

- System prompt (conceptual, sent to **Gemini**):
  - You are a factual Groww Mutual Fund FAQ assistant.
  - Only use the provided context snippets taken from Groww public pages.
  - If the answer is not in the context, say you do not know.
  - Never provide advice, recommendations, or opinions.
  - Answer concisely (2–5 sentences).
  - Do not generate URLs yourself; a single `source_url` will be appended by the backend.

- Inputs to the LLM:
  - Structured facts (for scheme queries).
  - Retrieved context chunks with their text.
  - The user’s latest question and a short conversation history.

### 4.2 Citation Handling

- The backend is responsible for **choosing exactly one `source_url`** (based on the retrieval logic) and appending:
  - `Source: <URL>`
  to the final answer.
- This avoids inconsistent or multiple citations from the LLM.

---

## Phase 5 – Backend Modules & APIs

### 5.1 Services / Modules

- **Ingestion (offline / CLI)**
  - `fetch_pages.py`: download and store raw HTML.
  - `parse_pages.py`: parse HTML into structured tables and unstructured chunks.
  - `build_embeddings.py`: compute and store embeddings in vector DB.

- **API Service (FastAPI)**
  - `intent_classifier.py`: classify user messages and extract attributes/scheme names.
  - `retriever.py`: hybrid retrieval over SQL and vector DB.
  - `rag_orchestrator.py`: builds prompts, enforces guardrails, calls LLM, attaches single source URL.
  - `routes.py`: exposes `POST /api/chat` and `GET /api/health`.

### 5.2 Key Endpoint – `/api/chat`

- Input:
  - `session_id`
  - `messages` (chat history)
- Processing steps:
  1. Run intent classification.
  2. Resolve scheme (if applicable).
  3. Perform structured lookup and/or vector retrieval based on intent.
  4. Build context + structured facts and call the LLM (unless refusing).
  5. Select a single `source_url` and attach to the answer.
- Output:
  - `answer`
  - `source_url`
  - `intent_type`
  - `scheme_slug` (if relevant)
  - `refusal`

---

## LLM Usage Summary (Gemini)

- **Gemini is the primary model** wherever a large language model is required in this architecture:
  - **Phase 2**: use a Gemini embeddings model for vector embeddings (Section 2.1).
  - **Phase 3**: optional use of Gemini chat/completions for intent classification and entity extraction (Section 3.2).
  - **Phase 4**: core use of Gemini for RAG answer generation with guardrails and citation control (Section 4.1).


---

## Phase 6 – React Chatbot Frontend

### 6.1 Tech Stack

- **React + TypeScript**.
- Optional UI library: Chakra UI / Material UI / Mantine for layout.

### 6.2 Components

- `ChatApp`
  - Holds `messages` state: `{ id, role, content, sourceUrl?, intentType?, refusal? }`.
  - Calls `POST /api/chat` on user input.
- `MessageList`
  - Renders user and assistant bubbles.
  - For assistant messages:
    - Shows the answer text.
    - Shows a small, clear citation at the bottom, e.g.:
      - `Source: Groww` as a link to `sourceUrl`.
- `ChatInput`
  - Textarea or input field + send button.
  - Handles Enter/submit events and clears input after sending.

### 6.3 UX Behaviour

- Show a loading indicator during backend calls.
- If `refusal` is true:
  - Display a clear explanation that the assistant cannot give investment advice, along with any allowed factual details.
- Allow users to click the source link to verify the information on Groww’s website.

---

## Phase 7 – Evaluation & Iteration (Pre-Deployment)

- Create a test set of user questions:
  - Scheme-specific: expense ratio, exit load, min SIP, risk level, benchmark, etc. for each supported HDFC fund.
  - Definitions and fee-related questions.
  - Advice queries and out-of-scope questions.
- Evaluate:
  - Factual correctness against Groww pages.
  - Correctness of chosen source URL.
  - Guardrail behavior (no advice, correct refusals).
- Refine:
  - Intent rules and scheme name resolution.
  - Parsing robustness for scheme pages.
  - Chunking and retrieval filters to improve precision and recall.

---

## Phase 8 – Scheduler & Periodic Refresh

Although deployment is out of scope, we define a scheduler phase so the ingestion pipeline can be refreshed automatically when deployed later.

### 8.1 Responsibilities

- Periodically:
  - Re-fetch the configured Groww URLs.
  - Re-parse pages into structured and unstructured content.
  - Recompute embeddings only for pages that changed (based on hash/etag/last-modified).
  - Update the SQL database and vector index with new chunks and embeddings.
- Ensure the chatbot always uses the **latest** public information from Groww within reasonable latency (e.g. daily refresh).

### 8.2 Implementation Sketch

- **Scheduler mechanism** (to be enabled in deployment):
  - Use a cron-like scheduler:
    - e.g. `cron`/systemd timer, or a Python scheduler (APScheduler) in a separate worker process.
  - Schedule jobs such as:
    - `daily_fetch_and_parse` (e.g. every night).
    - `daily_embedding_refresh` (after parsing).
- **Job entry points** (reusing ingestion modules):
  - `python fetch_pages.py --all`
  - `python parse_pages.py --changed-only`
  - `python build_embeddings.py --changed-only`

### 8.3 Consistency & Safety

- Use transactional updates in the database so partial refreshes do not corrupt the knowledge base.
- Optionally:
  - Write to shadow tables/indexes, then atomically swap them once a full refresh completes.
  - Log job status and errors for observability.

This additional scheduler phase completes the architecture with a clear place to plug in periodic ingestion once the system is deployed, while earlier phases already cover the backend APIs and React frontend.

