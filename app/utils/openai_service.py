import json
from datetime import datetime
from app.utils.openai_caption import call_ai
from app.utils.openai_image import generate_match_image
from app.utils.caption_logger import log_premium_caption_history
from app.extensions import db
from app.models import XPost, XPostMetrics
from app.utils.db_helpers import safe_commit

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

    bullets = ["→", "-", "•"]
    if any(w in text.lower() for w in bullets):
        score += 20

    if text.count("\n") >= 1:
        score += 20

    return min(score, 100)


def score_monetization(text):
    score = 0

    strong_ctas = ["follow", "subscribe", "join", "link in bio"]
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

def detect_niche(text):
    sports_keywords = ["match", "goal", "score", "football", "nba", "transfer", "penalty"]
    if any(k in text.lower() for k in sports_keywords):
        return "sports"
    return "growth"

def ai_suggest_best_time(text, user=None):
    """
    Use AI to suggest a best posting time based on content + niche.
    The AI prompt instructs it to use research about *where X engagement is highest*.
    """
    niche = detect_niche(text)
    prompt = f"""
Based on social media engagement research for X (formerly Twitter):

- For {niche} content specifically,
- Considering global audience patterns for engagement,
- Suggest a single best posting hour in HH:00 format.

Content:
\"\"\"{text}\"\"\"
Only return the best hour.
"""
    ai_response = call_ai(prompt, max_tokens=10)
    return ai_response.strip()

def suggest_best_post_time(user=None, text=None):
    # 1) Historical data
    if user and user.is_premium:
        posts = XPost.query.filter_by(user_id=user.id).all()
        hour_scores = {}
        for post in posts:
            metrics = XPostMetrics.query.filter_by(post_id=post.id).first()
            if metrics:
                hour = post.created_at.hour
                hour_scores.setdefault(hour, []).append(metrics.engagement_score)
        if hour_scores:
            avg_scores = {h: sum(s)/len(s) for h, s in hour_scores.items()}
            return f"{max(avg_scores, key=avg_scores.get):02d}:00"

    # 2) AI + research (best fallback)
    if text:
        best_time = ai_suggest_best_time(text, user)
        if best_time:
            return best_time

    # 3) Hard fallback safe default
    return "12:00"

def call_ai_thread(text, max_tweets=4, niche="growth", breaking=False):
    """
    Generate a structured thread:
    - Hook first tweet
    - Middle content
    - Engagement ending
    """

    niche_instruction = (
        "Focus on tactical value and structured insight."
        if niche == "growth"
        else "Focus on emotion, match dynamics, and fan reactions."
    )

    breaking_instruction = (
        "This is BREAKING NEWS. Prioritize clear and verified facts."
        if breaking else ""
    )

    prompt = f"""
You are an expert X thread strategist.

Rules:
- First tweet must have a hook (<12 words)
- Each tweet <= 260 characters
- No fluff
- No hashtags unless natural

{niche_instruction}
{breaking_instruction}

Topic:
\"\"\"{text}\"\"\"

Return a JSON array of tweet texts.
"""

    ai_response = call_ai(prompt, max_tokens=400)
    try:
        thread = json.loads(ai_response)
        if isinstance(thread, list):
            return thread[:max_tweets]
    except:
        lines = [l.strip() for l in ai_response.split("\n") if l.strip()]
        return lines[:max_tweets]

    return []

def generate_caption(text, user, tone="neutral", mode="single", max_output_chars=280, avoid_clickbait=False):
    tone = (tone or "neutral").lower()
    mode = (mode or "single").lower()
    niche = detect_niche(text)

    SYSTEM_PROMPT = f"""
You are an elite X strategist specializing in {niche} content.

You engineer posts for:
- Scroll stopping hooks
- High retention
- Psychological triggers
- Niche authority

Rules:
- Max {max_output_chars} characters
- First line under 12 words
- No fluff
- No cliched phrases
- No AI language
"""

    if niche == "sports":
        reply_instruction = """
Replies should:
- Invite predictions
- Spark emotion
- Ask opinions about key moments
Avoid generic praise.
"""
    else:
        reply_instruction = """
Replies should:
- Ask meaningful follow-up questions
- Add strategic insight
- Encourage discussion
Avoid generic praise.
"""
    MODE_INSTRUCTIONS = {
        "single": "Write a single high-impact post.",
        "reply": "Write a reply-optimized post designed to spark responses.",
        "thread": "Write the first tweet of a high-retention thread.",
        "engagement": "Write a curiosity-driven post to maximize replies."
    }

    prompt = f"""
{SYSTEM_PROMPT}

Tone: {tone}
Mode: {MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS['single'])}
Avoid clickbait: {avoid_clickbait}

Return JSON:

{{
  "caption": "...",
  "replies": ["...", "...", "..."]
}}

Content:
\"\"\"{text}\"\"\"
"""

    max_tokens = 220  # enough for caption + replies
    ai_response = call_ai(prompt, max_tokens=max_tokens)

    try:
        data = json.loads(ai_response)
        caption = data.get("caption", "")[:max_output_chars]
        replies = data.get("replies", [])
    except:
        caption = ai_response[:max_output_chars]
        replies = []

    analysis = {
        "hook_score": score_hook(caption),
        "retention_score": score_retention(caption),
        "monetization_score": score_monetization(caption),
        "niche": niche,
        "psychological_triggers": detect_psychological_triggers(caption)
    }

    image_url = generate_match_image(match_text=text) if generate_images else None

    best_post_time = suggest_best_post_time(user=user, text=text)

    return [{
        "style": "engineered",
        "text": post_text,
        "analysis": analysis,
        "best_post_time": best_post_time,
        "image_url": image_url
    }]

    return caption, replies, analysis

def generate_x_post_for_user(
    text,
    user,
    teams=None,
    event_time=None,
    tone="neutral",
    mode="single",
    avoid_clickbait=False,
    custom_prompt=None,
    max_output_chars=280
):
    tone = (tone or "neutral").lower()
    niche = detect_niche(text)
    generate_images = niche == "sports"

    thread_texts = []
    thread_images = []

    if mode in ["thread", "reply", "engagement"]:
        thread_texts = call_ai_thread(text, max_tweets=4, niche=niche, breaking=(tone == "breaking"))
        if generate_images:
            for t in thread_texts:
                thread_images.append(generate_match_image(match_text=t, teams=teams, event_time=event_time))

    if custom_prompt:
        wrapped = f"Generate ONE X post (≤280 chars) based on:\n{custom_prompt}"
        max_tokens = max_output_chars // 4
        post_text = call_ai(wrapped, max_tokens=max_tokens)
        post_text = post_text[:max_output_chars]
        captions = [{
            "style": "custom",
            "text": post_text,
            "suggested_replies": generate_replies(post_text, niche=niche) if user.is_premium else [],
            "best_post_time": suggest_best_post_time(user=user, text=custom_prompt),
            "image_url": generate_match_image(match_text=post_text) if generate_images else None
        }]
    else:
        captions = generate_captions(
            text=text,
            user=user,
            tone=tone,
            mode=mode,
            avoid_clickbait=avoid_clickbait,
            generate_images=generate_images,
            max_output_chars=max_output_chars
        )

    if user.is_premium:
        replies_flat = []
        for c in captions:
            replies_flat += generate_replies(c["text"], niche=niche)

        log_premium_caption_history(
            user=user,
            input_text=text,
            captions=captions,
            thread=[{"text": t, "image_url": i} for t, i in zip(thread_texts, thread_images)],
            replies=replies_flat,
            platform="x",
            tone=tone,
            length=mode
        )

    for cap in captions:
        new_post = XPost(
            user_id=user.id,
            text=cap["text"],
            style=cap["style"],
            engagement_score=cap["analysis"]["hook_score"],
            created_at=datetime.now()
        )
        db.session.add(new_post)
        db.session.flush()
        db.session.add(XPostMetrics(post_id=new_post.id, engagement_score=cap["analysis"]["hook_score"]))

    safe_commit()

    return {
        "type": "premium" if user.is_premium else "free",
        "captions": captions,
        "thread": [{"text": t, "image_url": i} for t, i in zip(thread_texts, thread_images)],
        "replies": [r for cap in captions for r in generate_replies(cap["text"], niche=niche)],
        "best_post_time": suggest_best_post_time(user=user, text=text),
        "engagement_score": max(cap["analysis"]["hook_score"] for cap in captions),
        "images": [cap["image_url"] for cap in captions]
    }
