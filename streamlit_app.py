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

SCHEMES = [
    "HDFC Mid Cap Fund",
    "HDFC Equity Fund",
    "HDFC Arbitrage Fund",
    "HDFC Liquid Fund",
    "HDFC Value Fund",
    "HDFC Tax Saver Fund",
]

QUESTION_LIBRARY = {
    "Basics (Mutual Funds)": [
        "What are mutual funds?",
        "How do mutual funds work?",
        "What is NAV in mutual funds?",
        "How is NAV calculated?",
        "What is the difference between SIP and lump sum?",
        "What is SIP and how does it work?",
        "What is a lump sum investment in mutual funds?",
        "What is the difference between direct and regular mutual fund plans?",
        "What is the difference between growth and IDCW options?",
        "What is AUM in mutual funds?",
        "What is the benchmark index in mutual funds?",
        "What is the risk level in mutual funds and what does it mean?",
    ],
    "Charges & Fees": [
        "What is an expense ratio in mutual funds?",
        "What is expense ratio and how is it charged?",
        "What is exit load in mutual funds?",
        "When is exit load applicable?",
        "What are the charges applicable for redeeming mutual funds on Groww?",
        "Are there any charges for switching mutual funds?",
        "Are there any charges for investing in mutual funds on Groww?",
        "How do mutual fund charges impact returns over time?",
    ],
    "Reports (Groww)": [
        "What mutual fund reports are available on Groww?",
        "How can I download mutual fund reports on Groww?",
        "What information is included in mutual fund reports?",
    ],
    "HDFC AMC (Facts)": [
        "What is HDFC Mutual Funds (AMC)?",
        "Which mutual fund schemes are offered by HDFC Mutual Funds on Groww?",
    ],
    "Scheme facts (HDFC)": [],
}

# Scheme-specific factual questions for ALL supported attributes / pages in scope.
for scheme in SCHEMES:
    QUESTION_LIBRARY["Scheme facts (HDFC)"].extend(
        [
            f"What is the expense ratio of {scheme}?",
            f"What is the exit load of {scheme}?",
            f"What is the minimum SIP amount of {scheme}?",
            f"What is the minimum lump sum amount of {scheme}?",
            f"What is the risk level of {scheme}?",
            f"What is the benchmark index of {scheme}?",
            f"What is the category of {scheme}?",
            f"Which AMC manages {scheme}?",
        ]
    )

def _unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = x.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


ALL_SAMPLE_QUESTIONS = _unique_keep_order([q for qs in QUESTION_LIBRARY.values() for q in qs])

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
if "topic" not in st.session_state:
    st.session_state.topic = "All"
if "home_query" not in st.session_state:
    st.session_state.home_query = ""
if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""
if "chat_limit" not in st.session_state:
    st.session_state.chat_limit = 18

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

/* Homepage hero */
.groww-hero {
  padding: 18px 16px;
  border-radius: 18px;
  border: 1px solid rgba(34,197,94,0.22);
  background:
    radial-gradient(900px 340px at 8% 0%, rgba(0, 203, 112, 0.18) 0%, rgba(2,6,23,0) 55%),
    linear-gradient(180deg, rgba(2,6,23,0.5) 0%, rgba(2,6,23,0.15) 100%);
}
.groww-kicker {
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(203, 213, 225, 0.85);
}
.groww-title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #f8fafc;
}
.groww-subtitle {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(226, 232, 240, 0.9);
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
        """
<div class="groww-hero">
  <div class="groww-kicker">Groww • Mutual Funds • Facts only</div>
  <div class="groww-title">Meet your Mini Mutual Fund Friend</div>
  <div class="groww-subtitle">
    Ask factual questions about <b>expense ratios</b>, <b>exit loads</b>, <b>redemption charges</b>,
    and <b>selected HDFC mutual fund scheme facts</b> — answered from Groww’s public pages.
    No recommendations, no opinions.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    m = st.columns(3)
    with m[0]:
        st.metric("In-scope schemes", str(len(SCHEMES)))
    with m[1]:
        st.metric("Sample questions", str(len(ALL_SAMPLE_QUESTIONS)))
    with m[2]:
        st.metric("Topics", str(len(QUESTION_LIBRARY.keys())))

    st.markdown("### Explore")
    tcols = st.columns([1, 1])
    with tcols[0]:
        st.session_state.topic = st.selectbox(
            "Pick a topic",
            ["All"] + list(QUESTION_LIBRARY.keys()),
            index=(["All"] + list(QUESTION_LIBRARY.keys())).index(st.session_state.topic)
            if st.session_state.topic in (["All"] + list(QUESTION_LIBRARY.keys()))
            else 0,
        )
    with tcols[1]:
        st.session_state.home_query = st.text_input("Search questions", value=st.session_state.home_query)

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
        # Filter library by topic + search
        topic = st.session_state.topic
        if topic != "All":
            base = QUESTION_LIBRARY.get(topic, [])
        else:
            base = ALL_SAMPLE_QUESTIONS

        q = (st.session_state.home_query or "").strip().lower()
        filtered = [x for x in base if (q in x.lower())] if q else list(base)
        filtered = _unique_keep_order(filtered)

        st.caption(f"Showing **{len(filtered)}** questions. Click any question on the chat screen to ask instantly.")

        holder = st.empty()
        # Reveal one-by-one as an animation, only after clicking the button.
        for i in range(st.session_state.samples_revealed, len(filtered)):
            st.session_state.samples_revealed = i + 1
            with holder.container():
                for text in filtered[: st.session_state.samples_revealed]:
                    st.markdown(f"- {text}")
            time.sleep(0.06)

        st.markdown("### Ask by click (no typing)")
        click_cols = st.columns(2)
        for idx, text in enumerate(filtered[: min(len(filtered), 12)]):
            with click_cols[idx % 2]:
                if st.button(text, key=f"home_click_{idx}", use_container_width=True):
                    st.session_state.pending_prompt = text
                    st.session_state.page = "chat"
                    st.rerun()

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

    st.markdown("### Click to ask")
    f1, f2 = st.columns([1, 1])
    with f1:
        chat_topic = st.selectbox(
            "Topic",
            ["All"] + list(QUESTION_LIBRARY.keys()),
            key="chat_topic_select",
        )
    with f2:
        st.session_state.chat_query = st.text_input("Search", value=st.session_state.chat_query, key="chat_search_input")

    if chat_topic != "All":
        base = QUESTION_LIBRARY.get(chat_topic, [])
    else:
        base = ALL_SAMPLE_QUESTIONS

    q = (st.session_state.chat_query or "").strip().lower()
    filtered = [x for x in base if (q in x.lower())] if q else list(base)
    filtered = _unique_keep_order(filtered)

    st.caption(f"Question library: **{len(filtered)}** results.")

    if st.button("Load more", use_container_width=True):
        st.session_state.chat_limit = min(st.session_state.chat_limit + 18, len(filtered))
        st.rerun()

    grid = st.columns(2)
    for idx, text in enumerate(filtered[: st.session_state.chat_limit]):
        with grid[idx % 2]:
            if st.button(text, key=f"chat_click_{idx}", use_container_width=True):
                st.session_state.pending_prompt = text
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
