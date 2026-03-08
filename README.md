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

Then open the URL shown (e.g. http://localhost:8501). No separate API server is needed; the app runs the RAG pipeline directly.

## Deploy backend on Streamlit Community Cloud

Deploy the **all-in-one chat app** (RAG + Streamlit UI) on Streamlit. No separate API server.

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and **New app**.
3. Connect the repo and set **Main file path:** `streamlit_app.py`.
4. Add **Secrets** (App settings → Secrets), for example:

   ```toml
   OPENROUTER_API_KEY = "your-openrouter-api-key"
   OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
   OPENROUTER_CHAT_MODEL = "openrouter/auto"
   ```

5. Deploy. The first run will install dependencies and may download the sentence-transformers model.

**Note:** The app needs the knowledge base (`data/kb.sqlite`). Build it locally (fetch_pages → parse_pages → build_embeddings) and commit `data/kb.sqlite`, or run ingestion in a one-off job if your host supports it.

## Deploy frontend on Vercel

Deploy **only the React (Vite) frontend** to Vercel. The chat UI will call a backend API; you must run the backend on a different platform (see below).

**Do not deploy the FastAPI backend on Vercel.** Vercel has a **500 MB** limit; this project’s dependencies are much larger. Run the backend on **Streamlit** (all-in-one chat UI) or **Render** (API for the React frontend).

1. **Backend options**
   - **Streamlit (all-in-one):** Deploy `streamlit_app.py` on Streamlit Community Cloud (see above). No separate API; the Streamlit app is the chat UI and backend.
   - **Render (API for Vercel frontend):** Use the FastAPI backend so the Vercel React app can call it:
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

2. **Deploy the frontend on Vercel** (Root Directory = `frontend`):
   - Go to [vercel.com](https://vercel.com), sign in, and **Add New Project**.
   - Import your GitHub repo.
   - Set **Root Directory** to `frontend` (or leave root and set Build/Output in the next step).
   - **Build settings:** Root Directory `frontend`, Build Command `npm run build`, Output Directory `dist`, Install Command `npm install`.
   - Add **Environment Variable:** `VITE_API_URL` = your **Render** backend URL (e.g. `https://your-app.onrender.com`) with **no trailing slash**. The frontend will call `{VITE_API_URL}/api/chat`.
   - Deploy.

3. **Local dev with backend:** In `frontend/.env` set `VITE_API_URL=http://127.0.0.1:8000` when running the FastAPI backend locally, or use the Vite proxy (see `frontend/vite.config.mts`).
