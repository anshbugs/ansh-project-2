"""
Groww Mutual Fund FAQ Chat — Streamlit app.

Frontend-only Streamlit UI that talks to the FastAPI backend:
- GET  /api/health
- POST /api/chat

Run from project root:
    streamlit run streamlit_app.py

On Streamlit Community Cloud: set BACKEND_URL in App settings → Secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import requests
import streamlit as st

# Must be first Streamlit command (required by Streamlit Cloud)
st.set_page_config(
    page_title="Groww MF Assistant",
    page_icon="https://groww.in/groww-logo-270.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Load Streamlit secrets into env (Streamlit Cloud)
try:
    if hasattr(st, "secrets") and st.secrets:
        for key in ("BACKEND_URL",):
            try:
                val = st.secrets.get(key) if hasattr(st.secrets, "get") else getattr(st.secrets, key, None)
                if val is not None and str(val).strip():
                    os.environ[key] = str(val).strip()
            except Exception:
                pass
except Exception:
    pass

DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

def _post_chat(backend_url: str, messages: List[Dict[str, str]], session_id: Optional[str]) -> Dict[str, Any]:
    r = requests.post(
        f"{backend_url}/api/chat",
        json={"session_id": session_id, "messages": messages},
        timeout=90,
    )
    if r.status_code >= 400:
        try:
            payload = r.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
        except Exception:
            detail = None
        raise RuntimeError(detail or f"Backend error {r.status_code}: {r.text}")
    return r.json()


def _health(backend_url: str) -> bool:
    try:
        r = requests.get(f"{backend_url}/api/health", timeout=8)
        return r.ok
    except Exception:
        return False

WELCOME = (
    "Hi, I'm your Groww Mutual Fund FAQ assistant. I can answer factual questions "
    "about selected HDFC mutual fund schemes and mutual fund charges using information "
    "from Groww's public pages.\n\n"
    "I cannot provide investment advice, opinions, or recommendations."
)

if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME, "source_url": None}]
if "error" not in st.session_state:
    st.session_state.error = None

# Minimal card-style CSS
st.markdown("""
<style>
.stApp { background: radial-gradient(1200px 600px at 10% 0%, rgba(34,197,94,0.10) 0%, rgba(2,6,23,0) 60%), linear-gradient(180deg, #0b1220 0%, #020617 100%); }
.main .block-container { max-width: 560px; margin: 26px auto; padding: 0; }
.main .block-container > div { background: rgba(15,23,42,0.92); border: 1px solid rgba(148,163,184,0.18); border-radius: 16px; padding: 18px; margin-bottom: 10px; box-shadow: 0 18px 60px rgba(0,0,0,0.45); }
header { visibility: hidden; }
footer { visibility: hidden; }

/* Chat typography */
.stChatMessage .stMarkdown p { font-size: 0.98rem; line-height: 1.55; letter-spacing: 0.1px; }
.stChatMessage [data-testid="stChatMessageContent"] { padding-top: 6px; }
</style>
""", unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.markdown("### Settings")
    st.session_state.backend_url = st.text_input("Backend URL", value=st.session_state.backend_url).rstrip("/")
    st.session_state.session_id = st.text_input("Session ID (optional)", value=st.session_state.session_id or "").strip() or None
    st.caption("Tip: for Docker Compose, use `http://backend:8000`.")

# Header
online = _health(st.session_state.backend_url)
status_dot = "#22c55e" if online else "#f59e0b"
status_text = "Online" if online else "Offline"
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(148,163,184,0.25);">
  <div style="display:flex;align-items:center;gap:10px;">
    <img src="https://groww.in/groww-logo-270.png" alt="Groww" style="height:28px;border-radius:6px;" />
    <div>
      <div style="font-size:15px;font-weight:600;color:#f9fafb;">Groww Mutual Fund Assistant</div>
      <div style="font-size:12px;color:#cbd5e1;">Interactive RAG chatbot (Streamlit UI → FastAPI backend)</div>
    </div>
  </div>
  <span style="font-size:11px;color:{status_dot};">● {status_text}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("**Try asking:** Expense ratio of HDFC Mid Cap Fund · Exit load for HDFC Equity Fund · What are the charges?")

if not online:
    st.warning(
        f"Backend not reachable at `{st.session_state.backend_url}`. "
        "Start the API with `uvicorn backend.app:app --host 127.0.0.1 --port 8000` or update the URL in the sidebar."
    )

if st.session_state.error:
    st.error(st.session_state.error)
    st.session_state.error = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source_url"):
            st.caption(f"[View source on Groww]({msg['source_url']})")

if prompt := st.chat_input("Ask about HDFC mutual fund facts, charges…"):
    st.session_state.messages.append({"role": "user", "content": prompt, "source_url": None})
    st.session_state.error = None
    with st.spinner("Thinking…"):
        try:
            payload = _post_chat(
                st.session_state.backend_url,
                [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ("user", "assistant")],
                st.session_state.session_id,
            )
            st.session_state.messages.append({
                "role": "assistant",
                "content": (payload.get("answer") or "").strip() or "No answer was generated. Please try again.",
                "source_url": payload.get("source_url"),
            })
        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err:
                st.session_state.error = "API rate limit exceeded. Please try again in a minute."
            else:
                st.session_state.error = err
    st.rerun()
