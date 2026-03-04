"""
Groww Mutual Fund FAQ Chat — Streamlit app.

Run from project root:
    streamlit run streamlit_app.py

Uses the same RAG backend (backend.rag_orchestrator) as the FastAPI app.
UI matches the React ChatWidget layout and styles.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

# Ensure project root is on path when running: streamlit run streamlit_app.py
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from backend.rag_orchestrator import chat, ChatResponse

st.set_page_config(
    page_title="Groww MF Assistant",
    page_icon="https://groww.in/groww-logo-270.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Match React app: card, header, bubbles, input, footer
STREAMLIT_CSS = """
<style>
/* Page background – same as React body */
.stApp {
  background: radial-gradient(circle at top left, #0f172a, #020617 50%, #020617 100%) !important;
}

/* Single column card: max-width 420px, centered. All content blocks get card bg */
.main .block-container {
  max-width: 420px !important;
  padding: 0 !important;
  margin: 24px auto !important;
  background: transparent !important;
}

/* Every block (except we'll exclude first if it's style-only) gets card background */
.main .block-container > div {
  background: rgba(15, 23, 42, 0.95) !important;
  margin: 0 !important;
  padding: 0 !important;
  border-left: 1px solid rgba(148, 163, 184, 0.3) !important;
  border-right: 1px solid rgba(148, 163, 184, 0.3) !important;
  box-shadow: none !important;
  color: #e5e7eb !important;
}

/* First content block: top rounded corners */
.main .block-container > div:first-of-type {
  border-radius: 20px 20px 0 0 !important;
  border-top: 1px solid rgba(148, 163, 184, 0.3) !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6) !important;
}

/* Last block: bottom rounded corners */
.main .block-container > div:last-of-type {
  border-radius: 0 0 20px 20px !important;
  border-bottom: 1px solid rgba(148, 163, 184, 0.3) !important;
}

/* Single block: all corners rounded */
.main .block-container > div:only-of-type {
  border-radius: 20px !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6) !important;
}

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ----- Header (React .chat-header) ----- */
.streamlit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.6), rgba(37, 99, 235, 0.5));
}
.streamlit-header-main { display: flex; align-items: center; gap: 10px; }
.streamlit-logo-wrap {
  height: 32px; width: 32px; border-radius: 9px; padding: 2px;
  background: rgba(15, 23, 42, 0.95);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 0 1px rgba(15, 118, 110, 0.6), 0 8px 20px rgba(15, 23, 42, 0.9);
}
.streamlit-logo { height: 26px; width: 26px; border-radius: 7px; display: block; }
.streamlit-title { font-size: 15px; font-weight: 600; color: #f9fafb; margin: 0; }
.streamlit-subtitle { font-size: 12px; color: #e5e7eb; opacity: 0.9; margin: 2px 0 0 0; }
.streamlit-status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  background: rgba(15, 23, 42, 0.8); color: #a7f3d0; font-size: 11px;
  border: 1px solid rgba(16, 185, 129, 0.5);
}
.streamlit-status-dot {
  width: 7px; height: 7px; border-radius: 999px;
  background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.9);
}

/* ----- Hint row ----- */
.streamlit-hint-row { padding: 10px 16px 6px; }
.streamlit-hint-label { font-size: 11px; color: #9ca3af; margin-bottom: 6px; }
.streamlit-hint-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.streamlit-chip {
  font-size: 11px; padding: 4px 8px; border-radius: 999px;
  background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.35);
  color: #e5e7eb;
}

/* ----- Messages area ----- */
.streamlit-messages {
  max-height: 420px; min-height: 220px; overflow-y: auto;
  padding: 10px 16px 8px; display: flex; flex-direction: column; gap: 6px;
}
.msg-row { display: flex; }
.msg-row-user { justify-content: flex-end; }
.msg-row-assistant { justify-content: flex-start; }
.msg-bubble {
  max-width: 82%; border-radius: 18px; padding: 8px 11px;
  font-size: 13px; line-height: 1.5;
}
.msg-bubble-user {
  background: linear-gradient(135deg, #22c55e, #059669); color: #022c22;
  border-bottom-right-radius: 4px;
}
.msg-bubble-assistant {
  background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.4);
  border-bottom-left-radius: 4px;
}
.msg-content p { margin: 0 0 4px; }
.msg-content p:last-child { margin-bottom: 0; }
.msg-meta { margin-top: 6px; font-size: 11px; }
.msg-source-link { color: #93c5fd; text-decoration: none; }
.msg-source-link:hover { text-decoration: underline; }

/* ----- Chat input area (Streamlit places at bottom) ----- */
.stChatInput > div { background: rgba(15, 23, 42, 0.96) !important; border-top: 1px solid rgba(148, 163, 184, 0.25) !important; padding: 8px 16px 12px !important; }
.stChatInput input, .stChatInput textarea { background: rgba(15, 23, 42, 0.9) !important; color: #e5e7eb !important; border: 1px solid rgba(148, 163, 184, 0.6) !important; border-radius: 14px !important; }
.stChatInput button { background: linear-gradient(135deg, #22c55e, #16a34a) !important; color: #022c22 !important; font-weight: 600 !important; border-radius: 999px !important; }

/* ----- Footer note ----- */
.streamlit-footer-note { padding: 4px 16px 14px; font-size: 10px; color: #9ca3af; border-top: 1px solid rgba(148, 163, 184, 0.25); background: rgba(15, 23, 42, 0.96); }
.streamlit-footer-note strong { color: #9ca3af; }

/* Error */
.streamlit-error { font-size: 11px; color: #fecaca; background: rgba(248, 113, 113, 0.1); border-radius: 6px; padding: 4px 8px; margin: 4px 16px; }
</style>
"""


def _escape_and_paragraphs(text: str) -> str:
    """Escape HTML and turn newlines into <p> for display inside .msg-content."""
    escaped = html.escape(text)
    parts = [p.strip() for p in escaped.split("\n") if p.strip()]
    if not parts:
        return "<p></p>"
    return "".join(f"<p>{p}</p>" for p in parts)


WELCOME = (
    "Hi, I'm your Groww Mutual Fund FAQ assistant. I can answer factual questions "
    "about selected HDFC mutual fund schemes and mutual fund charges using information "
    "from Groww's public pages.\n\n"
    "I cannot provide investment advice, opinions, or recommendations."
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME, "source_url": None},
    ]
if "error" not in st.session_state:
    st.session_state.error = None

# ----- Card content in one container (CSS + header, hints, messages, footer) -----
with st.container():
    st.markdown(STREAMLIT_CSS, unsafe_allow_html=True)
    # ----- Header (same as React) -----
    st.markdown(
        """
        <div class="streamlit-header">
            <div class="streamlit-header-main">
                <div class="streamlit-logo-wrap">
                    <img src="https://groww.in/groww-logo-270.png" alt="Groww" class="streamlit-logo" />
                </div>
                <div>
                    <div class="streamlit-title">Groww Mutual Fund Assistant</div>
                    <div class="streamlit-subtitle">Factual answers from Groww's HDFC MF pages</div>
                </div>
            </div>
            <div class="streamlit-status-pill">
                <span class="streamlit-status-dot"></span> Online
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ----- Try asking chips -----
    st.markdown(
        """
        <div class="streamlit-hint-row">
            <div class="streamlit-hint-label">Try asking:</div>
            <div class="streamlit-hint-chips">
                <span class="streamlit-chip">Expense ratio of HDFC Mid Cap Fund</span>
                <span class="streamlit-chip">Exit load for HDFC Equity Fund</span>
                <span class="streamlit-chip">Charges for redeeming units</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ----- Error -----
    if st.session_state.error:
        st.markdown(
            f'<div class="streamlit-error">{html.escape(st.session_state.error)}</div>',
            unsafe_allow_html=True,
        )
        st.session_state.error = None

    # ----- Messages as custom bubbles (same as React) -----
    st.markdown('<div class="streamlit-messages">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        role = msg["role"]
        content_html = _escape_and_paragraphs(msg["content"])
        row_class = "msg-row-user" if role == "user" else "msg-row-assistant"
        bubble_class = "msg-bubble-user" if role == "user" else "msg-bubble-assistant"
        source_url = msg.get("source_url")
        source_html = ""
        if role == "assistant" and source_url:
            source_html = f'<div class="msg-meta"><a href="{html.escape(source_url)}" target="_blank" rel="noreferrer" class="msg-source-link">View source on Groww</a></div>'
        st.markdown(
            f'<div class="msg-row {row_class}"><div class="msg-bubble {bubble_class}"><div class="msg-content">{content_html}</div>{source_html}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ----- Footer note -----
    st.markdown(
        '<div class="streamlit-footer-note">Answers are factual summaries from Groww\'s public pages and are <strong>not investment advice</strong>.</div>',
        unsafe_allow_html=True,
    )

# ----- Chat input (Streamlit places it after the container) -----
prompt = st.chat_input("Ask about HDFC mutual fund facts, charges, or definitions…")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt, "source_url": None})
    st.session_state.error = None
    with st.spinner("Thinking…"):
        try:
            resp: ChatResponse = chat(prompt)
            answer = resp.answer
            source_url = resp.source_url or ""
        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err:
                answer = "API rate limit exceeded. Please try again in a minute."
                source_url = ""
            else:
                st.session_state.error = str(e)
                answer = ""
                source_url = ""
    if answer:
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "source_url": source_url or None,
        })
    st.rerun()
