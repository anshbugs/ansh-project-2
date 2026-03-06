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

Deploy **only the React (Vite) frontend** to Vercel. The chat UI will call a backend API; you must run the backend on a different platform (see below).

**Do not deploy the FastAPI backend on Vercel.** Vercel uses AWS Lambda, which has a **500 MB ephemeral storage limit**. This project’s dependencies (e.g. `sentence-transformers`, PyTorch) are much larger (~7GB), so the backend will not fit. Deploy the backend on **Render**, **Railway**, **Fly.io**, or similar instead.

1. **Deploy the backend (FastAPI) on Render** (recommended) (not Vercel):
   - This repo includes a `render.yaml` that Render can auto-detect.
   - In Render: **New → Blueprint** and select your GitHub repo.
   - Set required environment variables:
     - `OPENROUTER_API_KEY` (required)
     - `OPENROUTER_CHAT_MODEL` (optional; default is `openrouter/auto`)
     - `OPENROUTER_BASE_URL` (optional; default is `https://openrouter.ai/api/v1`)
   - Set CORS so your frontend can call the backend:
     - `CORS_ALLOW_ORIGINS` = a comma-separated list of origins
       - Example: `https://your-frontend.vercel.app,http://localhost:5173`
       - Do not add a trailing slash
   - Confirm health after deploy: open `{YOUR_RENDER_URL}/api/health` and expect `{"status":"ok"}`.
   - **Knowledge base requirement:** the backend answers from the SQLite KB at `data/kb.sqlite`.
     - Simplest: build it locally (fetch → parse → embeddings) and commit `data/kb.sqlite` to the repo.
     - Or: create a Render persistent disk and populate `data/kb.sqlite` via a one-time run (advanced).

2. **Deploy only the frontend on Vercel** (Root Directory = `frontend`):
   - Go to [vercel.com](https://vercel.com), sign in, and **Add New Project**.
   - Import your GitHub repo.
   - Set **Root Directory** to `frontend` (or leave root and set Build/Output in the next step).
   - **Build settings:** Root Directory `frontend`, Build Command `npm run build`, Output Directory `dist`, Install Command `npm install`.
   - Add **Environment Variable:** `VITE_API_URL` = your backend URL (e.g. `https://your-app.onrender.com`) with **no trailing slash**. The frontend will call `{VITE_API_URL}/api/chat`.
   - Deploy.

3. **Local dev with backend:** In `frontend/.env` set `VITE_API_URL=http://127.0.0.1:8000` when running the FastAPI backend locally, or use a Vite proxy (see `frontend/vite.config.mts`).
