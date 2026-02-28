import json, re
from datetime import datetime
from datetime import time as dt_time
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

def suggest_best_post_time(user=None, ai_best_hour=None):
    # 1) Historical premium override
    if user and user.is_premium:
        # fetch posts with metrics in one query
        posts_with_metrics = (
            db.session.query(XPost, XPostMetrics)
            .join(XPostMetrics, XPost.id == XPostMetrics.post_id)
            .filter(XPost.user_id == user.id)
            .all()
        )

        if len(posts_with_metrics) >= 5:
            hour_scores = {}
            for post, metrics in posts_with_metrics:
                if metrics and metrics.engagement_score is not None:
                    hour = post.created_at.hour
                    hour_scores.setdefault(hour, []).append(metrics.engagement_score)

            if hour_scores:
                avg_scores = {h: sum(s)/len(s) for h, s in hour_scores.items()}
                best_hour = max(avg_scores, key=avg_scores.get)
                return f"{best_hour:02d}:00"

    # 2) AI fallback
    if ai_best_hour:
        return ai_best_hour

    # 3) Safe fallback
    return "12:00"

def generate_captions(text, user, tone="neutral", mode="single", max_tweets=4, niche="growth", breaking=False, max_output_chars=280, avoid_clickbait=False, custom_prompt=None, generate_images=False):

    tone = (tone or "neutral").lower()
    mode = (mode or "single").lower()
    niche = detect_niche(text)

    SYSTEM_PROMPT = f"""
You are an elite social media strategist for {niche} content on X (formerly Twitter). 
Your task: Generate ONE high-performing, premium X post and threads for {niche}.
Make it;
- High engagement (likes, replies, retweets)
- Scroll-stopping hooks
- High retention in threads
- Psychological triggers and niche authority

Rules:
- Max {max_output_chars} characters per post
- Include the exact rate (e.g., 26.5%) or specific policy action in the hook.
- Make the first line factual and specific to show expertise. 
- No fluff, no cliches, no AI language
- No hashtags unless natural
- Include emojis, excitement, and hooks
- Only recent, trending content
- Make it engaging, factual, and shareable
- If mode is NOT thread → include one best caption ONLY
- If mode is thread → caption must equal first tweet of thread
- Thread first tweet must be a hook
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
    niche_instruction = (
        "Focus on tactical value and structured insight."
        if niche == "growth"
        else "Focus on emotion, match dynamics, and fan reactions."
    )

    breaking_instruction = (
        "This is BREAKING NEWS. Prioritize clear and verified facts."
        if breaking else ""
    )

    MODE_INSTRUCTIONS = {
        "single": "Write a single high-impact post.",
        "reply": "Write a reply-optimized post designed to spark responses.",
        "thread": f"Write a complete {max_tweets}-tweet high-retention thread.",
        "engagement": "Write a curiosity-driven post to maximize replies."
    }

    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["single"])

    thread_rules = f"""
Thread Rules:
- If mode is NOT "thread", return "thread": []
- If mode is "thread":
  - Return exactly {max_tweets} tweets
  - Tweet 1 = hook (<12 words)
  - Tweet 2-3 = insight/value/emotion
  - Tweet {max_tweets} = strong close or CTA
"""

    prompt_content = custom_prompt or text
    thread_rules_text = thread_rules if mode=="thread" else ""
    prompt = f"""
{SYSTEM_PROMPT}

Tone: {tone}
Mode: {mode_instruction}
Avoid clickbait: {avoid_clickbait}
{niche_instruction}
{breaking_instruction}
{thread_rules_text}

Return JSON:

{{
  "caption": "...",
  "replies": ["...", "...", "..."],
  "thread": [],
}}

Content:
\"\"\"{prompt_content}\"\"\"
"""

    max_tokens = 250 if mode != "thread" else 500
    ai_response = call_ai(prompt, max_tokens=max_tokens) or ""

    try:
        data = json.loads(ai_response)
    except:
        data = {}

    caption = (data.get("caption") or "")[:max_output_chars]
    replies = data.get("replies", [])
    thread = data.get("thread", [])

    if mode == "thread":
      thread = thread[:max_tweets]
      while len(thread) < max_tweets:
        thread.append("Continue...")
    else:
      thread = []

    ai_best_hour = data.get("best_hour")
    if ai_best_hour and re.match(r"^\d{2}:00$", ai_best_hour):
        validated_hour = ai_best_hour
    else:
        validated_hour = None

    analysis = {
        "hook_score": score_hook(caption),
        "retention_score": score_retention(caption),
        "monetization_score": score_monetization(caption),
        "niche": niche,
        "psychological_triggers": detect_psychological_triggers(caption)
    }

    image_url = None
    if generate_images and niche == "sports":
        image_url = generate_match_image(match_text=caption)

    best_post_time = suggest_best_post_time(
        user=user,
        ai_best_hour=validated_hour
    )

    return [{
        "style": "engineered",
        "text": caption,
        "analysis": analysis,
        "suggested_replies": replies if user.is_premium else [],
        "thread": thread,
        "best_post_time": best_post_time,
        "image_url": image_url
    }]

def generate_x_post_for_user(
    text,
    user,
    teams=None,
    event_time=None,
    tone="neutral",
    mode="single",
    avoid_clickbait=False,
    custom_prompt=None,
    max_output_chars=280,
    generate_images=True
):
    tone = (tone or "neutral").lower()
    niche = detect_niche(text)

    captions = generate_captions(
      text=text,
      user=user,
      tone=tone,
      mode=mode,
      avoid_clickbait=avoid_clickbait,
      generate_images=generate_images,
      max_output_chars=max_output_chars,
      custom_prompt=custom_prompt
    )

    if niche != "sports":
        for cap in captions:
            cap["image_url"] = None

    thread_texts = captions[0].get("thread", [])
    thread_images = []
    if generate_images:
        for t in thread_texts:
            thread_images.append(
                generate_match_image(match_text=t, teams=teams, event_time=event_time)
            )

    if user.is_premium:
        replies_flat = [
            r for c in captions
            for r in c.get("suggested_replies", [])
        ]
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
        best_time_str = cap.get("best_post_time", "12:00")
        try:
            hour = int(best_time_str.split(":")[0])
            best_time_obj = dt_time(hour=hour)
        except:
            best_time_obj = None

        analysis = cap.get("analysis", {}) or {}

        confidence_score = (
            analysis.get("hook_score")
            or analysis.get("retention_score")
            or 0
        )
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
          best_post_time=best_time_obj,
          created_at=datetime.utcnow()
        )
        db.session.add(new_post)
        db.session.flush()
        db.session.add(XPostMetrics(post_id=new_post.id, engagement_score=None))

    final_best_time = captions[0].get("best_post_time")

    safe_commit()

    return {
        "type": "premium" if user.is_premium else "free",
        "captions": captions,
        "thread": [{"text": t, "image_url": i} for t, i in zip(thread_texts, thread_images)],
        "replies": [
            r for cap in captions
            for r in cap.get("suggested_replies", [])
        ],
        "best_post_time": final_best_time,
        "engagement_score": None,
        "images": [cap["image_url"] for cap in captions]
    }
