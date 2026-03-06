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

def generate_captions(text, user, tone="neutral", mode="single", max_tweets=4, niche="general", breaking=False, avoid_clickbait=False, platform="x", custom_prompt=None):

    tone = (tone or "neutral").lower()
    mode = (mode or "single").lower()
    is_premium = user and user.is_authenticated and user.is_premium
    caption_count = 3 if is_premium else 1

    SYSTEM_PROMPT = f"""
You are a professional social media Editor specializing in {niche}.
Your job is to generate high-performing social media captions based strictly on the user's provided topic.
Do NOT introduce unrelated political, economic, or news themes unless explicitly requested.
Follow these instructions:

1. **Focus**:
    - Ensure content is clear, engaging, and factual (or logical/entertaining if the topic is humorous), and shareable
    - Content must remain factual even when written in a viral style.
    - Do not invent facts.

2. **Engagement**: 
    - Maximize engagement through high engagement hooks, high retention in threads, and psychological triggers.
    - Create hooks that grab attention within the first line.
    - Maximize retention and encourage discussion in threads.
    - Use curiosity and contrast naturally to encourage engagement.

3. **Content Rules**:
    - Avoid filler language.
    - Keep writing clear, concise, and engaging.
    - Only include emojis or hashtags if they are natural and enhance engagement.

4. Platform Limits
- Never exceed the character limits defined by the platform rules.

Always base captions strictly on the text or custom prompt provided by the user.
"""

    if platform == "facebook":
        platform_instruction = """
Write for Facebook:
- Slightly longer (up to 500 characters)
- Conversational tone, encourage comments
- No hashtags unless natural
"""
    else:
        platform_instruction = """
Write for X:
- Short, sharp, punchy
- Under 280 characters
- Scroll-stopping content
"""

    clickbait_rule = (
    "Strictly avoid clickbait." if avoid_clickbait
    else "Clickbait is allowed if it increases engagement."
    )

    reply_instruction = """
Reply rules:
- Ask meaningful follow-up questions
- Add strategic insight
- Encourage discussion
- If not reply mode, replies should be empty.
Avoid generic praise.
"""

    MODE_INSTRUCTIONS = {
        "single": "Write 1 high-impact caption." if not is_premium else "Write 3 high-impact captions.",
        "3_captions": "Write 3 high-impact captions." if is_premium else "Write 1 caption only.",
        "engagement": f"Write a curiosity-driven caption(s) to maximize engagement and replies.",
        "reply": f"Write reply-style caption(s) designed to spark discussion and engagement.",
        "thread": "Create a structured multi-tweet thread.",
        "ultra_viral" : f"""
Generate ONE ultra-viral caption designed to explode engagement.

Rules for ultra_viral:
- Use shock, tension, boldness, contrast.
- Make it impossible to scroll past.
- It must feel controversial, powerful, or disruptive.
- If the caption feels weak, rewrite it stronger.
- If it exceeds 20 words, rewrite shorter.
"""
    }
    mode_instruction = MODE_INSTRUCTIONS.get(mode, "single post")

    TONE_INSTRUCTIONS = {

    "neutral": """
Neutral Tone Rules:
- Clear and straightforward.
- Informative without emotional bias.
- No exaggeration.
""",

    "breaking": """
Breaking Tone Rules:
- Urgent and direct.
- Prioritize clear and verified facts.
- Short sentences.
- Lead with the most important update.
- Avoid speculation.
""",

    "viral": """
Viral Tone Rules:
- Short, punchy sentences.
- Prioritize emotional impact over explanation.
- Use bold, high-contrast phrasing.
- Avoid formal or corporate tone.
- Maximum 20 words OR 120 characters preferred.
- Think like a headline that stops scrolling.
""",

    "emotional": """
Emotional Tone Rules:
- Trigger empathy or passion.
- Use strong feeling-based words.
- Personal, human-centered phrasing.
- Make readers feel involved.
""",

    "professional": """
Professional Tone Rules:
- Structured and authoritative.
- Fact-driven.
- Confident but not sensational.
- Clear and concise.
"""
    }
    tone_instruction = TONE_INSTRUCTIONS.get(tone, "")

    thread_rules = f"""
Thread Rules:
- If mode is NOT "thread", return "thread": []
- If mode is "thread", return exactly {max_tweets} tweets.
- Tweet 1 = Powerful factual Hook (<12 words)
- Tweet 2 to {max_tweets-1} = Insight/Emotion
- Tweet {max_tweets} = Strong closing insight or discussion trigger
- Each tweet under 280 characters
"""

    captions_template = "[" + ",".join(['{"text":"","replies":[]}' for _ in range(caption_count)]) + "]"
    prompt_content = custom_prompt or text
    thread_rules_text = thread_rules if mode=="thread" else ""
    prompt = f"""
{SYSTEM_PROMPT}

Tone: {tone}
{tone_instruction}
Mode: {mode_instruction}
{thread_rules_text}
{reply_instruction if mode=="reply" else ""}
Clickbait Rule:
{clickbait_rule}
Platform Rules:
{platform_instruction}

Return ONLY valid JSON using this exact structure.
Do not include any text before or after the JSON.

{{
 "captions": {captions_template},
 "thread":[]
}}

Content:
\"\"\"{prompt_content}\"\"\"
"""

    max_tokens = 300 if mode != "thread" else 500
    try:
        ai_response = call_ai(prompt, max_tokens=max_tokens) or ""
        if isinstance(ai_response, str):
          try:
              match = re.search(r'\{.*\}', ai_response, re.S)

              if match:
                  data = json.loads(match.group())
              else:
                  raise json.JSONDecodeError("No JSON found", ai_response, 0)
          except json.JSONDecodeError:
              log_safe("AI returned invalid JSON, using raw text fallback")
              data = {
                "captions": [{"text": ai_response, "replies": []}], "thread": []
              }
        elif isinstance(ai_response, dict):
            data = ai_response
            if "captions" not in data or not isinstance(data["captions"], list):
                data["captions"] = [{"text": ai_response.get("caption", ""), "replies": []}]
            if "thread" not in data or not isinstance(data["thread"], list):
                data["thread"] = []
        else:
            data = {
                "captions": [{"text": str(ai_response), "replies": []}],
                "thread": []
            }

    except json.JSONDecodeError:
        log_safe("AI returned invalid JSON, returning minimal fallback.")
        data = {
         "captions":[{"text": ai_response, "replies":[]}],
         "thread":[]
        }
    except Exception as e:
        log_safe("AI call completely failed: %s", e)
        data = {
         "captions":[{"text": ai_response, "replies":[]}],
         "thread":[]
        }

    raw_captions = data.get("captions", [])

    captions = []
    limit = caption_count

    for item in raw_captions[:limit]:

      text = (item.get("text") or "").strip()
      replies = item.get("replies") or []
      if not isinstance(replies, list):
          replies = [str(replies)]
      clean_replies = []
      for r in replies:
        if isinstance(r, str):
          r = r.strip()
          if r:
            if len(r) > 200:
              r = r[:200].rsplit(" ", 1)[0] + "..."
            clean_replies.append(r)

      captions.append({
          "style": tone,
          "text": text,
          "suggested_replies": clean_replies if is_premium else [],
          "thread": None
      })
    
    if not raw_captions:
      captions = [{
          "style": tone,
          "text": "⚠️ AI generation failed. Please check your internet connection and try again.",
          "suggested_replies": [],
          "thread": None
      }]

    thread = data.get("thread", [])

    # --- Thread normalization ---
    try:
      if mode == "thread":
          normalized_thread = []
          for t in thread[:max_tweets]:
              if isinstance(t, dict): normalized_thread.append(str(t.get("text","Continue...")))
              else: normalized_thread.append(str(t))
          while len(normalized_thread) < max_tweets:
              normalized_thread.append("Continue...")
          thread = normalized_thread
      else:
          thread = []
    except Exception:
        thread = []

    return captions, thread

def generate_x_post_for_user(
    text,
    user,
    tone="neutral",
    mode="single",
    platform="x",
    max_tweets=4,
    avoid_clickbait=False,
    custom_prompt=None,
):
    tone = (tone or "neutral").lower()
    niche = "general"

    captions, thread_data= generate_captions(
      text=text,
      user=user,
      tone=tone,
      mode=mode,
      platform=platform,
      avoid_clickbait=avoid_clickbait,
      custom_prompt=custom_prompt
    )

    is_premium = user and user.is_authenticated and user.is_premium

    if mode=="thread" and thread_data:
        thread_data = [t for t in thread_data if t not in [c['text'] for c in captions]]
        thread_data = thread_data[:max_tweets]

    if is_premium and captions:
          preview_text = captions[0]["text"] if captions else text
          first_cap = captions[0]

          new_post = XPost(
              user_id=user.id,
              original_text=text,
              text=preview_text,
              captions=captions,
              style=first_cap["style"],
              predicted_engagement=None,
              suggested_replies=first_cap.get("suggested_replies", []),
              threads=thread_data,
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
        "thread": [{"text": t} for t in thread_data] if thread_data else [],
        "replies": [
            r for cap in captions
            for r in cap.get("suggested_replies", []) if r
        ],
        "engagement_score": None
    }