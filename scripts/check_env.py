"""
Run from project root: python scripts/check_env.py

Checks that .env (or Streamlit secrets) would make OPENROUTER_API_KEY
available to the app. Does NOT print the key value.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env the same way the backend does
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

key = os.getenv("OPENROUTER_API_KEY")
key = (key or "").strip()

if not key:
    print("OPENROUTER_API_KEY: NOT SET")
    print("  -> Add it to .env (local) or Streamlit Secrets (Cloud).")
    sys.exit(1)

print("OPENROUTER_API_KEY: SET (length {} chars)".format(len(key)))
print("  -> Env is loading correctly; key is visible to the app.")
if key.startswith("sk-or-"):
    print("  -> Format looks like OpenRouter key (sk-or-...).")
else:
    print("  -> Key format may be wrong (OpenRouter keys usually start with sk-or-).")

base = os.getenv("OPENROUTER_BASE_URL", "").strip() or "default"
model = os.getenv("OPENROUTER_CHAT_MODEL", "").strip() or "default"
print("OPENROUTER_BASE_URL: {}".format(base if base != "default" else "default (https://openrouter.ai/api/v1)"))
print("OPENROUTER_CHAT_MODEL: {}".format(model if model != "default" else "default (from backend)"))
