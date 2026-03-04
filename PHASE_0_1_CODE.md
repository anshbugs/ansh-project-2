## Phase 0 & Phase 1 – Code Locations

This file points to the concrete code that implements **Phase 0 (Scope & Guardrails)** and **Phase 1 (Data Ingestion & Parsing)** for the Groww Mutual Fund FAQ RAG chatbot.

---

## Phase 0 – Scope & Guardrails Code

- **Main file**: `backend/config.py`
  - Defines the **allowed Groww URLs** that form the knowledge base:
    - `ALLOWED_KB_URLS`
  - Defines the **intent types** used by the backend:
    - `IntentType` enum (`SCHEME_FACT`, `GENERAL_DEFINITION`, `FEES_CHARGES`, `OTHER_FACTUAL`, `ADVICE_OR_OPINION`, `OUT_OF_SCOPE`)
  - Defines supported **scheme attributes** for factual queries:
    - `SUPPORTED_SCHEME_ATTRIBUTES` (e.g. `expense_ratio`, `exit_load`, `min_sip_amount`, etc.)
  - Defines **advice / opinion keywords** used to trigger refusals:
    - `ADVICE_KEYWORDS` (phrases like “should i invest”, “which is better”, “is it safe”, etc.)
  - Bundles all guardrail settings into:
    - `GuardrailConfig` dataclass
    - `GUARDRAILS` instance that can be imported by other backend modules.

These definitions are the single source of truth for what is in scope and what must be refused by the assistant.

---

## Phase 1 – Data Ingestion & Parsing Code

### 1.1 Dependencies

- **File**: `requirements.txt`
  - Contains dependencies used in Phase 1:
    - `requests` – HTTP fetching
    - `beautifulsoup4` – HTML parsing
    - `lxml` – fast HTML parser backend
    - `pydantic` – typed models (for later phases if needed)

Install with:

```bash
pip install -r requirements.txt
```

### 1.2 Storage Layer (SQLite Prototype)

- **File**: `backend/db.py`
  - Defines a small SQLite database for the prototype at `data/kb.sqlite`.
  - Creates tables when `init_db()` is called:
    - `raw_pages`
      - Stores fetched HTML for each Groww URL (`url`, `html`, `status_code`, `fetched_at`).
    - `mutual_fund_schemes`
      - Stores minimal structured attributes for HDFC schemes (`scheme_name`, `scheme_slug`, `underlying_url`, etc.).
    - `kb_chunks`
      - Stores unstructured **text chunks** with metadata (`chunk_id`, `url`, `page_type`, `scheme_slug`, `section_title`, `content`, `token_count`, `last_parsed_at`).
  - Exposes:
    - `get_connection()` – returns a SQLite connection.
    - `init_db()` – initialises all required tables.

### 1.3 Raw Page Fetcher (Phase 1.2)

- **File**: `backend/ingestion/fetch_pages.py`
  - Uses `ALLOWED_KB_URLS` from `backend.config`.
  - For each URL:
    - Fetches HTML using `requests` with a custom `User-Agent`.
    - Upserts an entry in the `raw_pages` table:
      - `url`, `html`, `status_code`, `fetched_at`.
  - Entry point:
    - `main()`:
      - Calls `init_db()`.
      - Iterates over all allowed URLs and fetches them.
  - CLI usage (from project root):

    ```bash
    python -m backend.ingestion.fetch_pages
    ```

### 1.4 Parsing & Chunking (Phase 1.3 / 1.4)

- **File**: `backend/ingestion/parse_pages.py`
  - Reads all rows from `raw_pages` and processes each page.
  - Functions:
    - `detect_page_type(url: str) -> str`
      - Classifies page as `scheme`, `amc`, `definition`, `blog`, `help`, or `other` based on the URL pattern.
    - `extract_scheme_slug(url: str) -> Optional[str]`
      - Extracts a short slug from scheme URLs (e.g. `hdfc-mid-cap-fund-direct-growth`).
    - `extract_main_text_chunks(soup: BeautifulSoup) -> List[(section_title, text)]`
      - Performs simple **heading-based chunking**:
        - Finds `h1`/`h2`/`h3` headings.
        - Groups following paragraphs/list items into sections until the next heading.
        - Returns `(section_title, combined_text)` pairs.
    - `upsert_scheme(...)`
      - For `scheme` pages:
        - Inserts or updates a minimal `mutual_fund_schemes` row using the page’s `<title>` and URL.
    - `insert_chunks(...)`
      - Writes each `(section_title, content)` pair as a row in `kb_chunks`, with:
        - `page_type`, `scheme_slug` (if any), `token_count`, `last_parsed_at`.
    - `parse_single_page(url, html)`
      - High-level function that:
        - Determines `page_type`.
        - Optionally updates `mutual_fund_schemes` for scheme pages.
        - Extracts unstructured chunks and inserts them into `kb_chunks`.
  - Entry point:
    - `main()`:
      - Calls `init_db()`.
      - Loads all rows from `raw_pages`.
      - Runs `parse_single_page` for each URL/HTML pair.
  - CLI usage:

    ```bash
    python -m backend.ingestion.parse_pages
    ```

Running **Phase 1** end-to-end:

```bash
python -m backend.ingestion.fetch_pages   # populate raw_pages
python -m backend.ingestion.parse_pages   # populate mutual_fund_schemes and kb_chunks
```

This file serves as a single place to see where the **code for Phase 0 and Phase 1** lives and how to run it, without mixing in later phases (embeddings, retrieval, backend API, frontend, or scheduler).

