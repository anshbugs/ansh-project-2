"""
Groww Mutual Fund FAQ Chat — Streamlit app.

All-in-one Streamlit app (UI + backend RAG pipeline in-process).

Run from project root:
    streamlit run streamlit_app.py

On Streamlit Community Cloud: set OPENROUTER_API_KEY (and optionally
OPENROUTER_BASE_URL, OPENROUTER_CHAT_MODEL) in App settings → Secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import time

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

SAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "What is the exit load for HDFC Equity Fund?",
    "What are the charges involved in mutual funds?",
    "What is NAV and how is it calculated?",
    "What is an exit load in mutual funds?",
    "What is the expense ratio in mutual funds?",
    "What is SIP and how does it work?",
    "What is a lump sum investment in mutual funds?",
    "What is the minimum SIP amount for HDFC funds on Groww?",
    "How are mutual fund returns taxed in India?",
    "What is STP and SWP in mutual funds?",
    "What is the difference between direct and regular mutual fund plans?",
    "What is the difference between growth and IDCW options?",
    "How does a mutual fund scheme’s AUM affect investors?",
    "What is the lock-in period for ELSS mutual funds?",
    "What is the risk level of HDFC Mid Cap Fund?",
    "What is the fund manager for HDFC Equity Fund?",
    "What is the category of HDFC Equity Fund?",
    "What is the benchmark index for HDFC Equity Fund?",
    "What is the investment objective of HDFC Mid Cap Fund?",
    "What is the minimum lump sum investment for HDFC Mid Cap Fund?",
    "What is the minimum SIP investment for HDFC Equity Fund?",
    "What is the exit load for HDFC Mid Cap Fund?",
    "What is the expense ratio of HDFC Equity Fund?",
    "What is the portfolio turnover ratio and why does it matter?",
    "What happens if I stop SIP payments?",
    "How long should I stay invested in an equity mutual fund?",
    "How do mutual fund charges impact returns over time?",
]

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
if "page" not in st.session_state:
    st.session_state.page = "home"  # "home" | "chat"
if "samples_revealed" not in st.session_state:
    st.session_state.samples_revealed = 0
if "show_samples" not in st.session_state:
    st.session_state.show_samples = False
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Minimal card-style CSS
st.markdown("""
<style>
.stApp { background: radial-gradient(1200px 600px at 10% 0%, rgba(0, 203, 112, 0.12) 0%, rgba(2,6,23,0) 60%), linear-gradient(180deg, #0b1220 0%, #020617 100%); }
.main .block-container { max-width: 560px; margin: 26px auto; padding: 0; }
.main .block-container > div { background: rgba(15,23,42,0.92); border: 1px solid rgba(148,163,184,0.18); border-radius: 16px; padding: 18px; margin-bottom: 10px; box-shadow: 0 18px 60px rgba(0,0,0,0.45); }
header { visibility: hidden; }
footer { visibility: hidden; }

/* Chat typography */
.stChatMessage .stMarkdown p { font-size: 0.98rem; line-height: 1.55; letter-spacing: 0.1px; }
.stChatMessage [data-testid="stChatMessageContent"] { padding-top: 6px; }

/* Buttons look more "app-like" */
div.stButton > button {
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,0.22);
  background: rgba(30, 41, 59, 0.55);
  color: #e5e7eb;
  transition: transform 120ms ease, background 120ms ease, border 120ms ease;
}
div.stButton > button:hover {
  background: rgba(34,197,94,0.14);
  border: 1px solid rgba(34,197,94,0.40);
  transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

def _render_header(subtitle: str) -> None:
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(148,163,184,0.25);">
  <div style="display:flex;align-items:center;gap:10px;">
    <img src="https://groww.in/groww-logo-270.png" alt="Groww" style="height:28px;border-radius:6px;" />
    <div>
      <div style="font-size:15px;font-weight:700;color:#f9fafb;letter-spacing:0.2px;">Groww Mutual Fund Assistant</div>
      <div style="font-size:12px;color:#cbd5e1;">{subtitle}</div>
    </div>
  </div>
  <span style="font-size:11px;color:#22c55e;">● Online</span>
</div>
""", unsafe_allow_html=True)


def _handle_user_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt, "source_url": None})
    st.session_state.error = None
    with st.spinner("Thinking…"):
        try:
            resp: ChatResponse = chat(prompt)
            st.session_state.messages.append({
                "role": "assistant",
                "content": (resp.answer or "").strip() or "No answer was generated. Please try again.",
                "source_url": resp.source_url,
            })
        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err:
                st.session_state.error = "API rate limit exceeded. Please try again in a minute."
            else:
                st.session_state.error = err


def _go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# Header (shared)
status_dot = "#22c55e"
status_text = "Online"

if st.session_state.page == "home":
    _render_header("Your mini mutual fund friend — facts from Groww pages")

    st.markdown(
        "Ask factual questions about **mutual fund charges**, **expense ratios**, **exit loads**, and "
        "**selected HDFC mutual fund scheme details** — answered from Groww’s public pages.\n\n"
        "When you’re ready, jump into the chat and just click a question to ask it."
    )

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Get list of sample questions to ask", use_container_width=True):
            st.session_state.show_samples = True
            st.session_state.samples_revealed = 0
    with cols[1]:
        if st.button("Try your mini mutual fund friend?", use_container_width=True):
            _go("chat")

    if st.session_state.show_samples:
        st.markdown("### Sample questions")
        holder = st.empty()
        # Reveal one-by-one as an animation, only after clicking the button.
        for i in range(st.session_state.samples_revealed, len(SAMPLE_QUESTIONS)):
            st.session_state.samples_revealed = i + 1
            with holder.container():
                for q in SAMPLE_QUESTIONS[: st.session_state.samples_revealed]:
                    st.markdown(f"- {q}")
            time.sleep(0.06)

elif st.session_state.page == "chat":
    _render_header("Interactive RAG chatbot (click questions, don’t type)")

    top = st.columns([1, 1])
    with top[0]:
        if st.button("← Back to homepage", use_container_width=True):
            _go("home")
    with top[1]:
        if st.button("New chat", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": WELCOME, "source_url": None}]
            st.session_state.error = None
            st.session_state.pending_prompt = None
            st.rerun()

    st.markdown("**Click to ask:**")
    grid = st.columns(2)
    for idx, q in enumerate(SAMPLE_QUESTIONS[:16]):
        with grid[idx % 2]:
            if st.button(q, key=f"sample_q_{idx}", use_container_width=True):
                st.session_state.pending_prompt = q
                st.rerun()

    st.markdown("---")

    if st.session_state.error:
        st.error(st.session_state.error)
        st.session_state.error = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("source_url"):
                st.caption(f"[View source on Groww]({msg['source_url']})")

    if st.session_state.pending_prompt:
        p = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        _handle_user_prompt(p)
        st.rerun()

    if prompt := st.chat_input("Or type a custom question…"):
        _handle_user_prompt(prompt)
        st.rerun()
