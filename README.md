# ansh-project-2

Groww Mutual Fund FAQ RAG chatbot prototype (Phases 0–3).

## Setup

1. **Install Python dependencies**:

   ```bash
   python -m pip install -r requirements.txt
   ```

   This includes:
   - `sentence-transformers` for **local embeddings** (model `all-MiniLM-L6-v2`).
   - `streamlit` for the Streamlit UI.
   - `fastapi`, `uvicorn`, and other backend/ingestion requirements.

2. **Configure your OpenRouter chat API key** in `.env` (in the project root):

   ```env
   OPENROUTER_API_KEY=your-openrouter-api-key
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_CHAT_MODEL=your-chat-model-id
   ```

   OpenRouter is used **only for chat completions**. All embeddings are computed locally.

## Run with Streamlit (recommended for deployment)

From the project root:

```bash
streamlit run streamlit_app.py
```

Then open the URL shown in the terminal (e.g. http://localhost:8501). No separate API server is needed; the app uses the RAG backend directly.

**First-time setup:** Ensure the knowledge base is built (see below) before using the chat.

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

## Deploy on Streamlit Community Cloud

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and **New app**.
3. Connect the repo and set:
   - **Main file path:** `streamlit_app.py`
   - **Branch:** your default branch
4. Add **Secrets** (in the app's settings or **Settings → Secrets**) so the app can read your API key. **If you see "OPENROUTER_API_KEY not set", add the key here.** For example:

   ```toml
   OPENROUTER_API_KEY = "your-openrouter-api-key"
   OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
   OPENROUTER_CHAT_MODEL = "your-chat-model-id"
   ```

5. Deploy. The first run will install dependencies from `requirements.txt` and download the sentence-transformers model; this can take a few minutes.

**Note:** The app needs the SQLite knowledge base (`data/kb.sqlite`) and embeddings. Either run the ingestion and embedding scripts locally and commit `data/kb.sqlite` to the repo (simple but the file can be large), or add a build step that runs fetch → parse → build_embeddings on first start.

**Optional:** To avoid the "unauthenticated requests to the HF Hub" warning and get faster model downloads, add `HF_TOKEN` to your Streamlit Secrets (create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)).

## Deploy frontend on Vercel

Deploy the **React (Vite) frontend** to Vercel. The chat UI will call a backend API; you need to run the backend elsewhere and point the frontend to it.

1. **Deploy the backend** (FastAPI) on Render, Railway, Fly.io, or similar:
   - Use the same repo; run `uvicorn backend.app:app --host 0.0.0.0 --port 8000` (or the port your host uses).
   - Set `OPENROUTER_API_KEY` (and optional `OPENROUTER_BASE_URL`, `OPENROUTER_CHAT_MODEL`) in the host’s environment.
   - Ensure the knowledge base exists (run fetch_pages, parse_pages, build_embeddings once, or include `data/kb.sqlite` in the deploy).

2. **Deploy the frontend on Vercel:**
   - Go to [vercel.com](https://vercel.com), sign in, and **Add New Project**.
   - Import your GitHub repo.
   - Set **Root Directory** to `frontend` (or leave root and set Build/Output in the next step).
   - **Build settings:** Root Directory `frontend`, Build Command `npm run build`, Output Directory `dist`, Install Command `npm install`.
   - Add **Environment Variable:** `VITE_API_URL` = your backend URL (e.g. `https://your-app.onrender.com`) with **no trailing slash**. The frontend will call `{VITE_API_URL}/api/chat`.
   - Deploy.

3. **Local dev with backend:** In `frontend/.env` set `VITE_API_URL=http://127.0.0.1:8000` when running the FastAPI backend locally, or use a Vite proxy (see `frontend/vite.config.mts`).
