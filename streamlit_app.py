"""
Groww Mutual Fund FAQ Chat — Streamlit app.

Run from project root:
    streamlit run streamlit_app.py

Uses the same RAG backend (backend.rag_orchestrator) as the FastAPI app.
"""

from __future__ import annotations

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

# Custom CSS for a cleaner chat layout and Groww-style link
st.markdown("""
<style>
    .stChatMessage { padding: 0.75rem 1rem; }
    .source-link { margin-top: 0.5rem; font-size: 0.9rem; }
    .source-link a { color: #00d09c; text-decoration: none; font-weight: 500; }
    .source-link a:hover { text-decoration: underline; }
    .disclaimer { font-size: 0.8rem; color: #666; margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

WELCOME = (
    "Hi, I'm your **Groww Mutual Fund FAQ** assistant. I can answer factual questions "
    "about selected HDFC mutual fund schemes and mutual fund charges using information "
    "from Groww's public pages.\n\n"
    "I cannot provide investment advice, opinions, or recommendations."
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME, "source_url": None},
    ]

# Header with logo and title
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image("https://groww.in/groww-logo-270.png", width=56)
with col_title:
    st.title("Groww Mutual Fund Assistant")
    st.caption("Factual answers from Groww's HDFC MF pages")

st.divider()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source_url"):
            st.markdown(
                f'<p class="source-link">Source: <a href="{msg["source_url"]}" target="_blank" rel="noreferrer">View on Groww</a></p>',
                unsafe_allow_html=True,
            )

# Input
if prompt := st.chat_input("Ask about HDFC mutual fund facts, charges, or definitions…"):
    st.session_state.messages.append({"role": "user", "content": prompt, "source_url": None})

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                resp: ChatResponse = chat(prompt)
                answer = resp.answer
                source_url = resp.source_url or ""
            except Exception as e:
                err = str(e)
                if "429" in err or "Too Many Requests" in err:
                    answer = (
                        "API rate limit exceeded. Please try again in a minute."
                    )
                    source_url = ""
                else:
                    answer = f"Something went wrong: {err}"
                    source_url = ""

        st.markdown(answer)
        if source_url:
            st.markdown(
                f'<p class="source-link">Source: <a href="{source_url}" target="_blank" rel="noreferrer">View on Groww</a></p>',
                unsafe_allow_html=True,
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "source_url": source_url or None,
        })

st.markdown(
    '<p class="disclaimer">Answers are factual summaries from Groww\'s public pages and are <strong>not investment advice</strong>.</p>',
    unsafe_allow_html=True,
)
