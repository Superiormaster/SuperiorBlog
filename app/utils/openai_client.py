import os
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

def openai_chat(prompt, model="gpt-4.1-mini"):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a content moderation assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    if r.status_code != 200:
        return None

    return r.json()["choices"][0]["message"]["content"]