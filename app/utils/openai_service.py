import json, re, logging
from datetime import datetime
from datetime import time as dt_time
from app.utils.openai_caption import call_ai
from app.extensions import db
from app.models import XPost, XPostMetrics
from app.utils.db_helpers import safe_commit

logger = logging.getLogger("caption")
logger.setLevel(logging.INFO)

def log_safe(msg, *args):
    try:
        logger.info(msg, *args)
    except Exception as e:
        print("Logging failed:", e)

def score_hook(text):
    first_line = text.strip().split("\n")[0]
    score = 0
    if len(first_line.split()) <= 12:
        score += 25
    if "?" in first_line:
        score += 15
    if any(char.isdigit() for char in first_line):
        score += 20
    keywords = ["why", "how", "this", "stop", "never", "no one", "everyone", "most people"]
    if any(w in first_line.lower() for w in keywords):
        score += 20
    return min(score, 100)

def score_retention(text):
    score = 0
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) >= 2:
        score += 20
    if len(text) <= 260:
        score += 20
    transitions = ["but", "however", "instead"]
    if any(w in text.lower() for w in transitions):
        score += 20
    bullets = ["→",  "'n", "-", "•"]
    if any(w in text.lower() for w in bullets):
        score += 20
    if text.count("\n") >= 1:
        score += 20
    return min(score, 100)

def score_monetization(text):
    score = 0
    strong_ctas = ["follow", "subscribe", "read", "link in comment section"]
    if any(w in text.lower() for w in strong_ctas):
        score += 40
    lead_magnets = ["guide", "free", "download", "course"]
    if any(w in text.lower() for w in lead_magnets):
        score += 30
    action_triggers = ["dm me", "comment", "reply"]
    if any(w in text.lower() for w in action_triggers):
        score += 30
    return min(score, 100)

def detect_psychological_triggers(text):
    triggers = []
    loss = ["fear", "risk", "lose"]
    curiosity = ["secret", "unknown", "no one tells"]
    contrast = ["most people", "everyone", "nobody"]
    authority = ["proof", "results", "data"]
    if any(w in text.lower() for w in loss):
        triggers.append("Loss Aversion")
    if any(w in text.lower() for w in curiosity):
        triggers.append("Curiosity Gap")
    if any(w in text.lower() for w in contrast):
        triggers.append("Social Contrast")
    if any(w in text.lower() for w in authority):
        triggers.append("Authority Signal")
    return triggers

def generate_captions(text, user, tone="neutral", mode="single", max_tweets=4, niche="news", breaking=False, max_output_chars=280, avoid_clickbait=False, platform="x", custom_prompt=None):

    tone = (tone or "neutral").lower()
    mode = (mode or "single").lower()
    is_premium = user and user.is_authenticated and user.is_premium

    SYSTEM_PROMPT = f"""
You are a professional social media Editor specializing in {niche}.
Your job is to research and generate high-performing captions for breaking or trending news.
Follow these instructions:

1. **Focus**: 
    - Political news, breaking updates, public policy, verified facts, emotional yet factual delivery.

2. **Engagement**: 
    - Maximize engagement through high engagement hooks, high retention in threads, and psychological triggers.

3. **Content Rules**: 
    - **Max {max_output_chars} characters per post.**
    - Include factual hooks and details (e.g., rates, policies).
    - No fluff, no clichés, avoid AI language.
    - Only include emojis or hashtags if they are natural and enhance engagement.
    - **Recent, trending content only.**
    - **If mode is "single"**: return only one high-performing post.
    - **If mode is "thread"**: return a complete thread, with the first tweet being a hook.
    - **High engagement**: Posts should be emotionally compelling, but not misleading.

Rules:
- Include the exact rate (e.g., 26.5%) or specific policy action in the hook.
- Make the first line factual and specific to show expertise. 
- Make it engaging, factual, and shareable
- Thread first tweet must be a hook
- Accurate and factual
- Clear first line with specific detail
- High engagement
- Encourage discussion

4. **Instructions for Specific Platforms**: 
    - **For X (Twitter)**: Short, punchy, and under 280 characters.
    - **For Facebook**: Slightly longer and more conversational (max 500 characters).
    
5. **Mode Instructions**: 
    - **single**: Return one post only.
    - **thread**: Return a complete {max_tweets}-tweet thread, with a strong hook in the first tweet.
    - **reply**: Generate a reply-optimized, Comment-style post designed to spark discussion
    - **engagement**: Generate Curiosity-driven posts designed to maximize engagement and replies.

6. **Breaking News**: 
    - If this is breaking news, prioritize clarity and verified facts.

7. **Avoid Clickbait**: 
    - Only include clickbait if the option is turned on (`avoid_clickbait=False`).
"""

    if platform == "facebook":
        platform_instruction = """
Write for Facebook:
- Slightly longer (up to 500 characters)
- Conversational, encourage comments
- No hashtags unless natural
"""
    else:
        platform_instruction = """
Write for X:
- Short, sharp, punchy
- Under 280 characters
- Scroll-stopping content
"""

    reply_instruction = """
Replies should:
- Ask meaningful follow-up questions
- Add strategic insight
- Encourage discussion
Avoid generic praise.
"""

    breaking_instruction = (
        "This is BREAKING NEWS. Prioritize clear and verified facts."
        if breaking else ""
    )

    MODE_INSTRUCTIONS = {
        "single": "Write a single high-impact post.",
        "reply": "Write a comment/reply-optimized post designed to spark responses and engagement.",
        "thread": f"Write a complete {max_tweets}-tweet high-retention thread with hooks and insight.",
        "engagement": "Write a curiosity-driven post to maximize replies."
    }
    mode_instruction = MODE_INSTRUCTIONS.get(mode, "single post")

    thread_rules = f"""
Thread Rules:
- If mode is NOT "thread", return "thread": []
- If mode is "thread", return exactly {max_tweets} tweets.
- Tweet 1 = Powerful factual Hook (<12 words)
- Tweet 2-3 = Insight/Emotion
- Last Tweet = Strong closing insight or discussion trigger
- Each tweet under 280 characters
- Clear separation of ideas
"""

    prompt_content = custom_prompt or text
    thread_rules_text = thread_rules if mode=="thread" else ""
    prompt = f"""
{SYSTEM_PROMPT}

Tone: {tone}
Mode: {mode_instruction}
Avoid clickbait: {avoid_clickbait}
{breaking_instruction}
{thread_rules_text}
Platform Rules:
{platform_instruction}

Return JSON:

{{
  "caption": "...",
  "replies": ["...", "...", "..."],
  "confidence_score": null,
  "thread": [],
}}

Content:
\"\"\"{prompt_content}\"\"\"
"""

    max_tokens = 250 if mode != "thread" else 500
    try:
        ai_response = call_ai(prompt, max_tokens=max_tokens) or ""
        data = json.loads(ai_response)
    except json.JSONDecodeError:
        # Fallback to safe default
        data = {
            "caption": text[:max_output_chars],
            "replies": [],
            "confidence_score": None,
            "thread": [text[:max_output_chars]] if mode == "thread" else []
        }
    except Exception as e:
        # Log any unexpected errors
        log_safe("AI call failed: %s", e)
        data = {
            "caption": "⚠️ Could not generate AI caption. Using default text.",
            "replies": [],
            "confidence_score": None,
            "thread": [text[:max_output_chars]] if mode == "thread" else []
        }

    caption = (data.get("caption") or "")[:max_output_chars]
    replies = data.get("replies", [])
    thread = data.get("thread", [])

    if mode == "thread":
        thread = data.get("thread", [])
        thread = [str(t) for t in thread][:max_tweets]
        while len(thread) < max_tweets:
            thread.append(caption if len(thread)==0 else "Continue...")
    else:
        thread = None

    hook = score_hook(caption)
    retention = score_retention(caption)
    monetization = score_monetization(caption)
    system_confidence = round(hook*0.4 + retention*0.4 + monetization*0.2, 1)

    confidence_score = data.get("confidence_score")
    if confidence_score is None:
        confidence_score = system_confidence

    analysis = {
        "hook_score": score_hook(caption),
        "retention_score": score_retention(caption),
        "monetization_score": score_monetization(caption),
        "niche": niche,
        "psychological_triggers": detect_psychological_triggers(caption)
    }

    return [{
        "style": "engineered",
        "text": caption,
        "analysis": analysis,
        "confidence_score": confidence_score,
        "suggested_replies": replies if is_premium else [],
        "thread": thread,
    }]

def generate_x_post_for_user(
    text,
    user,
    teams=None,
    event_time=None,
    tone="neutral",
    mode="single",
    platform="x",
    max_tweets=4,
    avoid_clickbait=False,
    custom_prompt=None,
    max_output_chars=280,
):
    tone = (tone or "neutral").lower()
    niche = "news"

    captions = generate_captions(
      text=text,
      user=user,
      tone=tone,
      mode=mode,
      platform=platform,
      avoid_clickbait=avoid_clickbait,
      max_output_chars=max_output_chars,
      custom_prompt=custom_prompt
    )

    is_premium = user and user.is_authenticated and user.is_premium

    thread = captions[0].get("thread", [])
    thread_texts = []
    if mode == "thread" and thread:
        for i in range(max_tweets):
            try:
                val = thread[i]
                thread_texts.append(val if isinstance(val, str) else str(val.get("text","Continue...")))
            except IndexError:
                thread_texts.append("Continue..." if i>0 else captions[0].get("text","No caption generated"))

    for cap in captions:
        confidence_score = cap.get("confidence_score", 0)
        analysis = cap.get("analysis", {}) or {}

        hook = int(analysis.get("hook_score") or 0)
        retention = int(analysis.get("retention_score") or 0)
        monetization = int(analysis.get("monetization_score") or 0)
        
        confidence_score = round(hook*0.4 + retention*0.4 + monetization*0.2, 1)

        if is_premium:
          new_post = XPost(
            user_id=user.id,
            text=cap["text"],
            style=cap["style"],
            confidence_score=confidence_score,
            predicted_engagement={
                "retention": analysis.get("retention_score", 0),
                "monetization": analysis.get("monetization_score", 0)
            },
            suggested_replies=cap.get("suggested_replies", []),
            created_at=datetime.utcnow()
          )
          try:
              db.session.add(new_post)
              db.session.flush()
              db.session.add(XPostMetrics(post_id=new_post.id, engagement_score=None))
              safe_commit()
          except Exception as e:
              db.session.rollback()
              log_safe("DB Write failed: %s", e)

    safe_commit()

    return {
        "type": "premium" if is_premium else "free",
        "captions": captions,
        "thread": [{"text": t} for t in thread_texts] if mode=="thread" else [],
        "replies": [
            r for cap in captions
            for r in cap.get("suggested_replies", []) if r
        ],
        "confidence_score": confidence_score or 0,
        "engagement_score": None
    }
