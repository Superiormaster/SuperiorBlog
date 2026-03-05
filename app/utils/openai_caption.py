import os
import requests
import time

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

def call_ai(prompt, max_tokens=200, temperature=0.7, retries=3, delay=2):
    """
    Calls the OpenAI API with automatic retries on network errors.
    
    Args:
        prompt (str): The user prompt to send to the AI.
        max_tokens (int): Maximum tokens to generate.
        temperature (float): Sampling temperature.
        retries (int): Number of retry attempts on failure.
        delay (float): Delay in seconds between retries.
    
    Returns:
        str: AI-generated response text.
    
    Raises:
        ValueError: If API key is missing.
        Exception: If all retries fail.
    """
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

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ AI network error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return {
                    "caption": "⚠️ Service temporarily unavailable. Try again later.",
                    "replies": [],
                    "confidence_score": 0,
                    "thread": []
                }
        except KeyError:
            print("⚠️ Unexpected response structure from AI API")
            return {
                "caption": "⚠️ Service temporarily unavailable. Try again later.",
                "replies": [],
                "confidence_score": 0,
                "thread": []
            }
        except Exception as e:
            print(f"❌ AI call failed: {e}")
            return {
                "caption": "⚠️ Service temporarily unavailable. Try again later.",
                "replies": [],
                "confidence_score": 0,
                "thread": []
            }