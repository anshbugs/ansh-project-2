# API entrypoint for ASGI servers

This folder exposes the FastAPI app for platforms that look for `api/index.py` or `api/app.py`.

**Do not use this for Vercel.** Vercel's serverless functions have a 500 MB storage limit; this project's dependencies (sentence-transformers, PyTorch, etc.) exceed that. Deploy the backend on **Render**, **Railway**, or **Fly.io** instead, and run:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Deploy only the **frontend** (the `frontend/` folder) on Vercel, and set `VITE_API_URL` to your backend URL.
