import os
import requests
from flask import flash
from app.utils.Xservice import HEADERS

"""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
  }"""

def generate_ai_caption(
    text,
    platform,
    tone,
    length,
    emoji_allowed,
    max_length, 
    style="safe", 
    trends=None, 
    monetize=False
):

    """
    Generate a single AI caption, style-aware.
    Free users: style ignored (safe).
    Premium users: style = safe / viral / editor_pick
    """
    # Style-based prompt tweak
    style_prompt = {
        "viral": "Make it exciting, attention-grabbing, and viral.",
        "editor_pick": "Make it insightful and professional, as if an editor chose it.",
        "safe": "Clear, concise, readable, trustworthy."
    }.get(style, "Clear and readable.")

    trend_prompt = f"Include trending hashtags or keywords: {', '.join(trends)}" if trends else ""
    monetize_prompt = "Suggest a subtle call-to-action for clicks or sign-ups." if monetize else ""

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
- scroll-stopping
- optional emoji
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

Rules per platform:
Facebook: conversational, human-like, optional CTA
X (Twitter): strong hook, under 280 chars, trending hashtags if available
LinkedIn: professional, informative

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

    prompt = f"""
You are a professional social media editor. 
Generate ONE high-quality caption based on the input text, optimized for the {platform} platform.
Include:
- Tone: {tone}
- Length: {length} characters
- Emojis allowed: {emoji_allowed}
- Style: {style}
- Trending prompts: {trend_prompt}
- Monetization: {monetize_prompt}

Return JSON:
{{
  "caption": "",
  "hashtags": [],
  "cta": "",
  "style": "{style}"
}}
Text to rewrite:
{text}
"""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional social media strategist."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 250
    }

    # existing request code...
    


def generate_ai_caption_x(
    text,
    tone,
    style="safe",
    max_length=260
):
    style_prompt = {
        "viral": "Make it bold, opinionated, and scroll-stopping.",
        "editor_pick": "Make it sharp, insightful, and newsroom-grade.",
        "safe": "Make it clear, factual, and engaging."
    }.get(style, "Clear and engaging.")

    prompt = f"""
You are a senior X (Twitter) editor.

Write ONE native X post.

Rules:
- Strong hook in first line
- One clear idea
- Max {max_length} characters
- No hashtags unless truly newsworthy
- No marketing language
- Optional emoji (max 1)
- Sound human, confident, and current
- Do NOT mention AI

STYLE:
{style_prompt}

TEXT:
{text}

Return ONLY the post text.
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You write high-performing X posts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 120
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()

    caption = r.json()["choices"][0]["message"]["content"].strip()
    return caption[:max_length]
    
# Free mode
def generate_x_post(text, style="safe", breaking=False, max_length=260):
    style_prompt = {
        "safe": "Clear, factual, human-written.",
        "viral": "Bold, opinionated, scroll-stopping.",
        "editor": "Sharp, authoritative, newsroom-grade."
    }[style]

    breaking_prompt = (
        "This is BREAKING NEWS. Lead with urgency and clarity. Avoid speculation."
        if breaking else
        ""
    )

    prompt = f"""
You are a senior X (Twitter) editor.

Write ONE native X post.

RULES:
- Strong hook in first line
- One clear idea
- Max {max_length} characters
- No hashtags unless truly necessary
- Optional emoji (max 1)
- No marketing language
- Do NOT mention AI

STYLE:
{style_prompt}

{breaking_prompt}

TEXT:
{text}

Return ONLY the post text.
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You write high-performing X posts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 120
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()

    return r.json()["choices"][0]["message"]["content"].strip()[:max_length]
    
# premium
def generate_x_thread(text, breaking=False, max_tweets=4):
    prompt = f"""
You are a senior X editor.

Turn the following text into a concise X THREAD.

RULES:
- {2}-{max_tweets} tweets
- Each tweet ≤ 260 characters
- Tweet 1 must hook strongly
- Logical flow across tweets
- No hashtags
- Optional emoji only in tweet 1
- No marketing language
- Do NOT mention AI

{"This is BREAKING NEWS. Prioritize clarity and verified facts." if breaking else ""}

TEXT:
{text}

Return STRICT JSON:
{{
  "thread": ["tweet 1", "tweet 2", "tweet 3"]
}}
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You write viral X threads."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=45)
    r.raise_for_status()

    return r.json()["choices"][0]["message"]["content"]

# Mixed
def generate_x_content(text, user):
    breaking = is_breaking_news(text)

    if not user.is_premium:
        # FREE USER
        caption = generate_x_post(
            text=text,
            style="safe",
            breaking=breaking
        )

        return {
            "type": "single",
            "captions": [{
                "style": "safe",
                "text": caption
            }]
        }

    # PREMIUM USER
    captions = []

    for style in ["safe", "viral", "editor"]:
        captions.append({
            "style": style,
            "text": generate_x_post(
                text=text,
                style=style,
                breaking=breaking
            )
        })

    thread = generate_x_thread(text, breaking=breaking)

    return {
        "type": "premium",
        "captions": captions,
        "thread": thread
    }
