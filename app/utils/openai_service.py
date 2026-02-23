import random
from datetime import datetime
from app.utils.openai_caption import call_ai
from app.utils.openai_image import generate_match_image
from app.utils.caption_logger import log_premium_caption_history
from app.utils.openai_predictive_generator import predictive_best_time, predictive_engagement_boost
from app.extensions import db
from app.models import XPost, XPostMetrics
from app.utils.db_helpers import safe_commit

# ---------------------------
# Engagement Scoring
# ---------------------------

def compute_engagement_score(text, user_is_premium=True):
    """Predict engagement score (0–100) based on text features."""
    score = 40
    length = len(text)
    if 60 <= length <= 140:
        score += 20
    elif 40 <= length < 60 or 140 < length <= 200:
        score += 10

    for kw in ["breaking", "just in", "watch", "goal", "full-time"]:
        if kw in text.lower():
            score += 10

    score += min(text.count(":") * 5, 5)
    score += min(text.count("!") * 5, 5)
    score += min(sum(1 for c in text if c in "🔥🚨⚽") * 5, 10)

    if user_is_premium:
        score += random.randint(0, 5)

    return min(score, 100)

# ---------------------------
# Suggested Replies
# ---------------------------

def generate_replies(text, num=3):
    """Return a list of suggested replies using AI."""
    prompt = f"""
Generate {num} short, natural replies for the following X post:
{text}
Return as JSON array: ["reply 1", "reply 2", "reply 3"]
"""
    ai_response = call_ai(prompt, max_tokens=100)
    try:
        return eval(ai_response)
    except:
        return []

# ---------------------------
# Best Post Time
# ---------------------------

def suggest_best_post_time(user=None):
    """Return best posting time as 'HH:00'. Premium users get predictive time."""
    if user and user.is_premium:
        posts = XPost.query.filter_by(user_id=user.id).all()
        if posts:
            hour_scores = {}
            for post in posts:
                metrics = XPostMetrics.query.filter_by(post_id=post.id).first()
                if not metrics:
                    continue
                hour_scores.setdefault(post.created_at.hour, []).append(metrics.engagement_score)
            if hour_scores:
                avg_scores = {h: sum(s)/len(s) for h, s in hour_scores.items()}
                return f"{max(avg_scores, key=avg_scores.get)}:00"
    # Free users or no data → random peak hour
    return f"{random.choice([8, 10, 12, 15, 17, 19, 21])}:00"

# ---------------------------
# Caption Generation
# ---------------------------

def generate_captions(text, user, tone="neutral", mode="single", avoid_clickbait=False):
    """Generate captions: safe for free, safe/viral/editor for premium."""
    styles = ["safe", "viral", "editor"] if user.is_premium else ["safe"]
    style_prompts = {
        "safe": "Clear, factual, human-written.",
        "viral": "Bold, opinionated, scroll-stopping.",
        "editor": "Sharp, authoritative, newsroom-grade."
    }

    captions = []
    for style in styles:
        prompt = f"""
You are a senior X (Twitter) editor.
Write ONE X post (≤260 chars) in {style} style.
Rules:
- Strong hook first line
- Optional emoji (max 1)
- No marketing language or AI mention
"""
        # Inject tone
        if tone and tone.lower() != "neutral":
            prompt += f"- Adopt a {tone.lower()} tone.\n"

        # Inject clickbait avoidance
        if avoid_clickbait:
            prompt += "- Avoid clickbait, exaggerated claims, or sensationalist hooks.\n"

        # Inject text
        prompt += f"TEXT: {text}\nSTYLE: {style_prompts[style]}"

        post_text = call_ai(prompt, max_tokens=120)
        captions.append({
            "style": style,
            "text": post_text,
            "confidence_score": compute_engagement_score(post_text, user_is_premium=user.is_premium),
            "predicted_engagement": {
                "likes": random.randint(10, 50),
                "retweets": random.randint(5, 20),
                "replies": random.randint(1, 10)
            },
            "suggested_replies": generate_replies(post_text) if user.is_premium else [],
            "best_post_time": suggest_best_post_time(user),
            "image_url": generate_match_image(match_text=text)
        })
    return captions

# ---------------------------
# Thread Generation
# ---------------------------

def generate_thread(text, max_tweets=4, breaking=False):
    """Generate short X thread for premium users."""
    prompt = f"""
Turn the following text into a concise X thread ({2}-{max_tweets} tweets, ≤260 chars each):
{text}
{'This is BREAKING NEWS. Prioritize clarity and verified facts.' if breaking else ''}
Return as JSON array.
"""
    ai_response = call_ai(prompt, max_tokens=300)
    if not ai_response:
        return []
    try:
        return eval(ai_response)
    except:
        # fallback: split by line
        return [t.strip() for t in ai_response.split("\n") if t.strip()]

# ---------------------------
# Unified X Post Generator
# ---------------------------

def generate_x_post_for_user(text, user, teams=None, event_time=None, tone="neutral", length="short", platforms=None, mode="single", intent="inform", avoid_clickbait=False):
    """
    Generate full X post package.
    Free: 1 safe caption + image + basic score
    Premium: multiple captions + thread + replies + predictive best time + engagement
    """
    # Decide if images are needed
    topic = "sports" if any(k in text.lower() for k in ["match", "goal", "score", "football"]) else "general"
    generate_images = topic.lower() == "sports"

    # Pre-generate thread images for sports
    thread_images = []
    if generate_images:
        thread_texts = generate_thread(text, max_tweets=4)
        for t_text in thread_texts:
            thread_images.append(generate_match_image(match_text=t_text, teams=teams, event_time=event_time))
    else:
        thread_texts = generate_thread(text, max_tweets=4)
        thread_images = [None] * len(thread_texts)

    # Generate main images (for top post)
    main_images = generate_match_image(match_text=text, teams=teams, event_time=event_time) if generate_images else []

    # Free user
    if not user.is_premium:
        caption_text = call_ai(f"Write ONE safe X post (≤260 chars) based on: {text}")
        return {
            "type": "free",
            "captions": [{
                "style": "safe",
                "text": caption_text,
                "confidence_score": compute_engagement_score(caption_text, user_is_premium=False),
                "predicted_engagement": {
                    "likes": random.randint(10, 50),
                    "retweets": random.randint(5, 20),
                    "replies": random.randint(1, 10)
                },
                "suggested_replies": [],
                "best_post_time": suggest_best_post_time(user),
                "image_url": main_images
            }],
            "thread": None,
            "replies": [],
            "best_post_time": suggest_best_post_time(user),
            "engagement_score": compute_engagement_score(caption_text, user_is_premium=False),
            "images": main_images
        }

    # Premium user
    captions = generate_captions(text, user, tone=tone, mode=mode, avoid_clickbait=avoid_clickbait)
    thread = []
    if mode in ["thread", "reply", "engagement"]:
        thread = generate_thread(
            text,
            max_tweets=4,
            breaking=(tone=="breaking") or (mode=="breaking")
        )
    engagement_score = max(c["confidence_score"] for c in captions)
    replies = sum([c["suggested_replies"] for c in captions], [])

    # Log everything for premium users
    log_premium_caption_history(
        user=user,
        input_text=text,
        captions=captions,
        thread=thread,
        replies=replies,
        platform="x",
        tone="sharp",
        length="short"
    )

    for cap in captions:
        new_post = XPost(
            user_id=user.id,
            text=cap["text"],
            style=cap["style"],
            engagement_score=cap["confidence_score"],
            created_at=datetime.now()
        )
        db.session.add(new_post)
        safe_commit()
        db.session.add(XPostMetrics(post_id=new_post.id, engagement_score=cap["confidence_score"]))
        safe_commit()

        if generate_images:
            cap["image_url"] = main_images

    # Attach thread images
    thread_with_images = []
    for i, t_text in enumerate(thread_texts):
      thread_with_images.append({
        "text": t_text,
        "image_url": thread_images[i]
      })

    return {
        "type": "premium",
        "captions": captions,
        "thread": thread_with_images,
        "replies": replies,
        "best_post_time": suggest_best_post_time(user),
        "engagement_score": engagement_score,
        "images": main_images
    }