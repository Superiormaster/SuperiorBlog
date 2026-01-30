import os
import requests
from flask import flash

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
  }

def generate_ai_caption(
    text,
    platform,
    tone,
    length,
    emoji_allowed,
    max_length, 
    style="safe"
):

    """
    Generate a single AI caption, style-aware.
    Free users: style ignored (safe).
    Premium users: style = safe / viral / editor_pick
    """
    # Style-based prompt tweak
    style_prompt = ""
    if style == "viral":
        style_prompt = "Make it exciting, attention-grabbing, and viral."
    elif style == "editor_pick":
        style_prompt = "Make it insightful and professional, as if an editor chose it."
    else:
        style_prompt = "Make it clear, concise, and readable."

    prompt = f"""
You are a professional social media editor for a modern news and creator platform.

Your task:
Generate ONE high-quality caption based on the input text.

Context:
- Platform: {platform}
- Tone: {tone}
- Desired length: {length}
- Emojis allowed: {emoji_allowed}
- Style: {style}

Rules:
- Match the writing style of the specified platform
- Be clear, engaging, and natural
- Stay under {max_length} characters
- Do NOT include hashtags unless the platform is Instagram
- {style_prompt}
- Avoid clickbait or misleading claims
- Output ONLY the caption text (no quotes, no labels, no explanations)

Text:
{text}
"""

    if not text:
        return {"error": "No input text provided"}

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You generate viral, professional captions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        r = requests.post(
            API_URL,
            headers=HEADERS,
            json=payload,
            timeout=60
        )

        if r.status_code != 200:
            flash("Network unavailable", "error")
            return {
              "caption": fallback_caption(text, platform, max_length=max_length),
              "error": "AI unavailable"
            }

        caption = r.json()["choices"][0]["message"]["content"].strip()
        return {"caption": caption[:max_length], "error": None}

    except requests.exceptions.Timeout:
        return {"error": "AI request timed out"}
    except Exception as e:
        print("❌ OpenAI caption error:", e)
        return {"caption": fallback_caption(text, platform, max_length=max_length), "error": "AI unavailable"}

def fallback_caption(text, platform, max_length=300):
    return f"{text[:max_length]} — via {platform.capitalize()}"

def confidence_score(text):
    """UX-based score (free fallback)."""
    score = 40

    length = len(text)

    # Length quality
    if 60 <= length <= 140:
        score += 20
    elif 40 <= length < 60 or 140 < length <= 200:
        score += 10

    # Engagement markers
    if any(word in text.lower() for word in ["breaking", "just in", "watch", "full-time"]):
        score += 10

    # Punctuation & flow
    if ":" in text:
        score += 5
    if "!" in text:
        score += 5

    # Controlled emoji boost
    emoji_count = sum(1 for c in text if c in "🔥🚨⚽")
    score += min(emoji_count * 5, 10)

    return min(score, 100)

def ai_confidence_score(text, platform, user_is_premium=True):
    """
    Hybrid score: UX + AI
    AI is only called for premium users to save cost.
    """
    ux_score = confidence_score(text)

    if not user_is_premium:
        return ux_score  # free users only get UX

    # Step 2: AI-based rating (0-100)
    prompt = f"""
Rate the following social media caption on {platform} from 0-100 for engagement, clarity, and virality. 
Respond with a single integer only.

Caption:
{text}
"""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional social media analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 10
    }

    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        ai_score = int(''.join(filter(str.isdigit, r.json()["choices"][0]["message"]["content"])))
        # Hybrid: 50% UX + 50% AI
        final_score = int((ux_score * 0.5) + (ai_score * 0.5))
        return final_score
    except Exception as e:
        print("❌ AI confidence error:", e)
        return ux_score