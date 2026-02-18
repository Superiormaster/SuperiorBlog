from datetime import datetime
import random
from app.models import CaptionHistory
from app.extensions import db
from app.utils.openai_caption import generate_x_post, confidence_score

# ------------------------------
# Daily Usage Tracker
# ------------------------------
def captions_today(user_id):
    today = datetime.utcnow().date()
    count = CaptionHistory.query.filter(
        CaptionHistory.user_id == user_id,
        CaptionHistory.created_at >= today
    ).count()
    return count or 0

# ------------------------------
# Platform Presets
# ------------------------------
PLATFORM_PRESETS = {
    'x': {'max': 280, 'emoji': True, 'tone': 'sharp'},
    'facebook': {'max': 500, 'emoji': True, 'tone': 'conversational'},
    'instagram': {'max': 300, 'emoji': True, 'tone': 'catchy'},
    'youtube': {'max': 400, 'emoji': False, 'tone': 'informative'},
    'linkedin': {'max': 350, 'emoji': False, 'tone': 'professional'},
}

# ------------------------------
# Detect Platform Automatically
# ------------------------------
def detect_platform(text):
    t = text.lower()
    if "thread" in t or "🚨" in t or "breaking" in t:
        return "x"
    if "#" in t:
        return "instagram"
    if any(word in t for word in ["career", "hiring", "professional"]):
        return "linkedin"
    return "facebook"

# ------------------------------
# Multi-Variation Caption Generator
# ------------------------------
def generate_caption(text: str, tone=None, length="short", user=None, platforms=None):
    if not text:
        return {
          "caption": "Please provide text to generate a caption.",
          "overall_confidence": 0,
          "reason": "No text was provided",
          "captions": []
        }

    # Default platform
    if not platforms:
        platforms = [detect_platform(text)]

    if any(word in text.lower() for word in [
        "breaking", "just in", "this changes", "here’s why", "thread", "full-time"
    ]):
        score += 15

    if platform != "x":
      emoji_count = sum(1 for c in text if c in "🔥🚨⚽")
      score += min(emoji_count * 5, 10)

    # Free users get only one platform
    if user and not getattr(user, "is_premium", False):
        platforms = platforms[:1]

    results = []

    for platform in platforms:
      platform = platform.lower()
      preset = PLATFORM_PRESETS.get(platform, {'max': 300, 'emoji': False, 'tone': 'neutral'})

      max_length = preset['max']
      emoji_allowed = preset['emoji']
      default_tone = preset['tone']
      tone = tone or default_tone
  
      captions_to_generate = 3 if getattr(user, "is_premium", False) else 1
      styles = ["safe", "viral", "editor_pick"][:captions_to_generate]

      multi_captions = []

      for style in styles:
        ai_result = generate_ai_caption(
            text=text,
            platform=platform,
            tone=tone,
            length=length,
            style=style,
            emoji_allowed=emoji_allowed,
            max_length=max_length
        )

        caption = ai_result.get("caption")
        error = ai_result.get("error")
        if not caption or error:
          continue
  
      # Emoji control
        if not emoji_allowed:
            caption = ''.join(c for c in caption if ord(c) < 128)
  
        if length == "short":
            caption = caption[:120]

        if platform != "x":
            if style == "viral":
                caption += " 🔥"
            elif style == "editor_pick":
                caption += " — Editor's choice"

        caption = caption[:max_length]

        confidence = ai_confidence_score(caption, platform, user_is_premium=getattr(user, "is_premium", False))
        """confidence_map = {
            "0": "calm",
            "1": "assertive",
            "2": "bold"
        }
        confidence = confidence_map.get(request.form["confidence"], "calm")
        """

      # Store results and DB logging
        multi_captions.append({
          "style": style,
          "caption": caption,
          "confidence": confidence,
          "reason": f"Generated for {platform} with {tone} tone and {length} length"
        })

      overall_confidence = max(
        (c["confidence"] for c in multi_captions),
        default=0
      )

      if not multi_captions:
        continue

      # Save history in DB
      db_entry = CaptionHistory(
        user_id=getattr(user, "id", None),
        platform=platform,
        tone=tone,
        length=length,
        caption=multi_captions[0]["caption"] if multi_captions else "",
        confidence=overall_confidence,
        input_text=text,
        captions=multi_captions
      )
      db.session.add(db_entry)
      db.session.commit()

      result = {
        "caption": multi_captions[0]["caption"] if multi_captions else "",
        "overall_confidence": overall_confidence,
        "captions": multi_captions
      }
      results.append(result)

    return results