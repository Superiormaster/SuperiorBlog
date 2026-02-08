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
You are a professional social media editor for a modern news and creator platform. You are a professional social media editor working for a news-driven creator platform.

Your task:
Generate ONE high-quality caption based on the input text. Rewrite the following content for four platforms using platform-native writing styles.
Your task is to rewrite the content below into platform-native captions.
Each platform must follow its natural writing behavior.

Context:
- Platform: {platform}
- Tone: {tone}
- Desired length: {length}
- Emojis allowed: {emoji_allowed}
- Writing style: {style}
- Confidence level: {confidence}

GLOBAL RULES:
- Writing style: {style}
- Confidence level: {confidence}
- Do NOT repeat the same wording across platforms
- Do NOT mention that this is AI-generated

PLATFORM RULES:

Instagram:
- Emotion-driven
- Engaging and scroll-stopping
- Light CTA if confidence is assertive or bold
- Hashtags allowed (max 5, relevant only)
- Emojis allowed only if confidence is bold (max 1)

Facebook:
- Conversational and explanatory
- Reads like a human wrote it
- No hashtags
- CTA only if promotional style

WhatsApp:
- Very short
- Headline-style
- No emojis
- No hashtags
- Feels like a status update

X (Twitter):
- Strong hook in first line
- Opinionated if style is opinionated
- Under 240 characters
- Emojis only if confidence is bold (max 1)


Rules:
- Match the writing style of the specified platform
- Be clear, engaging, and natural
- Stay under {max_length} characters
- Do NOT include hashtags unless the platform is Instagram
- {style_prompt}
- Avoid clickbait or misleading claims
- Output ONLY the caption text (no quotes, no labels, no explanations)
- Instagram: emotional, engaging, hashtags allowed
- Facebook: conversational, explanatory
- WhatsApp: short, headline-like
- X: strong hook, opinionated, under 240 characters

Return response strictly in JSON:
{
  "instagram": "",
  "facebook": "",
  "whatsapp": "",
  "x": ""
}

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