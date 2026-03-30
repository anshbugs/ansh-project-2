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
uvicorn backend.app:app --host 127.0.0.1 --port 8000
streamlit run streamlit_app.py
```

Then open the URL shown (e.g. http://localhost:8501). The Streamlit UI calls the FastAPI backend at `http://127.0.0.1:8000`.

## Deploy (Streamlit UI + hosted API)

This repo uses **Streamlit for the UI** and **FastAPI for the backend**.

1. **Deploy the FastAPI backend** (Render / Fly.io / Railway / your VPS / Docker).
2. **Deploy the Streamlit UI** on Streamlit Community Cloud:
   - Main file path: `streamlit_app.py`
   - Add Streamlit **Secrets**:

     ```toml
     BACKEND_URL = "https://your-backend-host"
     ```

3. **Required backend env vars** (set them where you host FastAPI):
   - `OPENROUTER_API_KEY` (required)
   - `OPENROUTER_BASE_URL` (optional; default `https://openrouter.ai/api/v1`)
   - `OPENROUTER_CHAT_MODEL` (optional; default `openrouter/auto`)

Confirm the backend:
- `GET {BACKEND_URL}/api/health` → `{"status":"ok"}`

**Note:** The backend needs the knowledge base (`data/kb.sqlite`). Build it locally (fetch_pages → parse_pages → build_embeddings) and commit `data/kb.sqlite`, or populate it on the host via a one-off ingestion run.

**(Removed)** The previous React/Vercel frontend has been removed in favor of Streamlit.
