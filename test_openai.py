import requests, os

API_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    "Content-Type": "application/json"
}
payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You generate captions."},
        {"role": "user", "content": "Test"}
    ],
    "temperature": 0.7,
    "max_tokens": 50
}

try:
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=25)
    print("Status code:", r.status_code)
    print("Response:", r.text)
except requests.exceptions.Timeout:
    print("❌ Request timed out. Check your network or increase timeout.")
except requests.exceptions.RequestException as e:
    print("❌ Request failed:", e)