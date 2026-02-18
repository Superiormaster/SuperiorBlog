from app.extensions import db

def log_premium_caption_history(user, input_text, captions=None, thread=None, replies=None, platform="x", tone="neutral", length="short"):
    from app.models import CaptionHistory
    """
    Logs full X post data into CaptionHistory **only for premium users**.
    
    Parameters:
    - user: current user object
    - input_text: original text used to generate captions
    - captions: list of caption dicts (style, caption, confidence, etc.)
    - thread: list of tweets (for X threads)
    - replies: list of suggested replies
    - platform: 'x', 'instagram', 'facebook', etc.
    - tone: caption tone ('sharp', 'conversational', etc.)
    - length: 'short' or 'long'
    """
    if not getattr(user, "is_premium", False):
        # Do not save anything for free users
        return None

    if not captions:
        captions = []

    overall_confidence = max((c.get("confidence", 0) for c in captions), default=0)

    db_entry = CaptionHistory(
        user_id=getattr(user, "id", None),
        platform=platform,
        tone=tone,
        length=length,
        caption=captions[0]["caption"] if captions else "",
        confidence=overall_confidence,
        input_text=input_text,
        captions=captions,
        thread=thread or [],
        replies=replies or []
    )
    db.session.add(db_entry)
    db.session.commit()
    return db_entry