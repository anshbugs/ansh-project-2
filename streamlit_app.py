"""
Groww Mutual Fund FAQ Chat — Streamlit app.

Runs the RAG pipeline in-process: no separate backend API.
- Uses backend.rag_orchestrator (classify → retrieve → generate).
- OpenRouter is called via backend.openrouter_client.
- Embeddings and retriever are unchanged (local embeddings + SQLite).

Run from project root:
    streamlit run streamlit_app.py

On Streamlit Community Cloud: set OPENROUTER_API_KEY (and optionally
OPENROUTER_BASE_URL, OPENROUTER_CHAT_MODEL) in App settings → Secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import streamlit as st

# Must be first Streamlit command (required by Streamlit Cloud)
st.set_page_config(
    page_title="Groww MF Assistant",
    page_icon="https://groww.in/groww-logo-270.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Load Streamlit secrets into env so backend.config can use them on Streamlit Cloud
try:
    if hasattr(st, "secrets") and st.secrets:
        for key in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_CHAT_MODEL"):
            try:
                val = st.secrets.get(key) if hasattr(st.secrets, "get") else getattr(st.secrets, key, None)
                if val is not None and str(val).strip():
                    os.environ[key] = str(val).strip()
            except Exception:
                pass
except Exception:
    pass

from backend.config import OPENROUTER_API_KEY
from backend.rag_orchestrator import chat, ChatResponse

if not OPENROUTER_API_KEY or not str(OPENROUTER_API_KEY).strip():
    st.error("OPENROUTER_API_KEY not set. Add it to .env (local) or Streamlit Secrets (deployed).")
    st.stop()

WELCOME = (
    "Hi, I'm your Groww Mutual Fund FAQ assistant. I can answer factual questions "
    "about selected HDFC mutual fund schemes and mutual fund charges using information "
    "from Groww's public pages.\n\n"
    "I cannot provide investment advice, opinions, or recommendations."
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME, "source_url": None}]
if "error" not in st.session_state:
    st.session_state.error = None

# Minimal card-style CSS
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #0f172a 0%, #020617 100%); }
.main .block-container { max-width: 420px; margin: 24px auto; padding: 0; }
.main .block-container > div { background: rgba(15,23,42,0.95); border-radius: 12px; padding: 16px; margin-bottom: 8px; }
header { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(148,163,184,0.25);">
  <div style="display:flex;align-items:center;gap:10px;">
    <img src="https://groww.in/groww-logo-270.png" alt="Groww" style="height:28px;border-radius:6px;" />
    <div>
      <div style="font-size:15px;font-weight:600;color:#f9fafb;">Groww Mutual Fund Assistant</div>
      <div style="font-size:12px;color:#e5e7eb;">Factual answers from Groww's HDFC MF pages</div>
    </div>
  </div>
  <span style="font-size:11px;color:#22c55e;">● Online</span>
</div>
""", unsafe_allow_html=True)

st.markdown("**Try asking:** Expense ratio of HDFC Mid Cap Fund · Exit load for HDFC Equity Fund")

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
            resp: ChatResponse = chat(prompt)
            st.session_state.messages.append({
                "role": "assistant",
                "content": resp.answer,
                "source_url": resp.source_url,
            })
        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err:
                st.session_state.error = "API rate limit exceeded. Please try again in a minute."
            else:
                st.session_state.error = err
    st.rerun()
