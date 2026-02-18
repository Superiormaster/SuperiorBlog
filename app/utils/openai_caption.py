import os
import requests

# ---------------------------
# Config
# ---------------------------
API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

# ---------------------------
# Helper functions
# ---------------------------

def call_ai(prompt, max_tokens=200, temperature=0.7):
    """Generic AI call"""
    if not OPENAI_API_KEY:
      raise ValueError("OPENAI_API_KEY is not set")
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional social media strategist for X (Twitter)."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("❌ AI Error:", e)
        return None