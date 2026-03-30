# ansh-project-2

Groww Mutual Fund FAQ RAG chatbot prototype (Phases 0–3).

## Setup

1. **Install Python dependencies**:

   ```bash
   python -m pip install -r requirements.txt
   ```

   This includes:
   - `sentence-transformers` for **local embeddings** (model `all-MiniLM-L6-v2`).
   - `fastapi`, `uvicorn`, and other backend/ingestion requirements.
   - `streamlit` for the Streamlit chat UI (optional; used when deploying on Streamlit Cloud).

2. **Configure your OpenRouter chat API key** in `.env` (in the project root):

   ```env
   OPENROUTER_API_KEY=your-openrouter-api-key
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_CHAT_MODEL=your-chat-model-id
   ```

   OpenRouter is used **only for chat completions**. All embeddings are computed locally.

## Run Phase 2 (embeddings) and Phase 3 (chat API)

To build the knowledge base and run the **FastAPI** backend (e.g. for the React frontend):

From the project root:

```bash
python -m backend.ingestion.fetch_pages   # Phase 1 – fetch Groww pages
python -m backend.ingestion.parse_pages   # Phase 1 – parse & chunk + structured fields
python -m backend.ingestion.build_embeddings  # Phase 2 – build local embeddings
uvicorn backend.app:app --host 127.0.0.1 --port 8000  # Phase 3 – chat API
```

If you see an error mentioning **`sentence-transformers` is not installed**, run:

```bash
python -m pip install sentence-transformers
```

## Run with Streamlit (local)

From the project root:

```bash
streamlit run streamlit_app.py
```

Then open the URL shown (e.g. http://localhost:8501). No separate API server is needed; the Streamlit app runs the RAG pipeline in-process.

## Deploy on Streamlit Community Cloud (UI + backend in one)

Streamlit Community Cloud runs a **single app process**, so this repo deploys as an **all-in-one Streamlit app** (UI + backend logic together).

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Repo: this repo, branch `main`, **Main file path:** `streamlit_app.py`.
4. Add Streamlit **Secrets** (App settings → Secrets):

   ```toml
   OPENROUTER_API_KEY = "your-openrouter-api-key"
   OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
   OPENROUTER_CHAT_MODEL = "openrouter/auto"
   ```

**Note:** The app needs the knowledge base (`data/kb.sqlite`). Build it locally (fetch_pages → parse_pages → build_embeddings) and commit `data/kb.sqlite`, or run ingestion in a one-off job if your host supports it.

**(Removed)** The previous React/Vercel frontend has been removed in favor of Streamlit.
