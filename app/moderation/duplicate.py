# duplicate.py
from app.models import Post
import hashlib, json
from difflib import SequenceMatcher
from ..utils.openai_client import openai_chat  # optional AI fallback

SIMILARITY_THRESHOLD = 0.90  # high similarity
AI_THRESHOLD_LOW = 0.75
AI_THRESHOLD_HIGH = 0.89

def hash_content(text: str) -> str:
    """Generate a SHA256 hash of the content."""

    if not isinstance(text, str):
        text = ""

    text = text.strip()
    text = text.lower()

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

def similarity(a, b) -> float:
    """Return similarity ratio between 0 and 1."""
    if not a or not b:   
        return 0.0

    a = str(a or "").strip().lower()
    b = str(b or "").strip().lower()
    return SequenceMatcher(None, a, b).ratio()

def check_post_duplicates(user_id: int, title: str, content: str, category=None, post_id=None):
    """
    Returns dict:
    {
        "exact_duplicate": bool,
        "high_similarity": bool,
        "ai_duplicate": bool
    }
    """
    review_flags = {
        "exact_duplicate": False,
        "high_similarity": False,
        "ai_duplicate": False
    }

    # 1️⃣ Check content hash (exact duplicate)
    content_hash = hash_content(content)
    if Post.query.filter_by(content_hash=content_hash).first():
        review_flags["exact_duplicate"] = True
        return review_flags  # stop immediately

    # 2️⃣ Get posts to compare
    query = Post.query
    # Filter by category if provided
    if category:
        if hasattr(category, "id"):
            query = query.filter(Post.category_id == category.id)
        elif isinstance(category, int):
            query = query.filter(Post.category_id == category)

    # Optionally skip current post (when editing)
    if post_id:
        query = query.filter(Post.id != post_id)

    existing_posts = query.order_by(Post.id.desc()).limit(50).all()

    # 3️⃣ Title similarity
    for post in existing_posts:
        title_score = similarity(title, post.title)
        if title_score >= SIMILARITY_THRESHOLD:
            review_flags["high_similarity"] = True
            break

    # 4️⃣ Content similarity
    for post in existing_posts:
        content_score = similarity(content, post.content)
        if content_score >= SIMILARITY_THRESHOLD:
            review_flags["high_similarity"] = True
            break
        elif AI_THRESHOLD_LOW <= content_score <= SIMILARITY_THRESHOLD:
            # optional: semantic AI check
            ai_result = ai_check_duplicate(content, post.content)
            if ai_result:
                review_flags["ai_duplicate"] = True
                break

    return review_flags

def ai_check_duplicate(new_content: str, existing_content: str) -> bool:
    """
    Calls OpenAI to check semantic similarity. 
    Only used if difflib similarity is borderline.
    """
    prompt = (
        "You are a content moderation assistant. "
        "Determine if the NEW content is semantically the same story as the EXISTING content. "
        "Respond ONLY with DUPLICATE or UNIQUE.\n\n"
        f"NEW CONTENT:\n{new_content[:1500]}\n\n"
        f"EXISTING CONTENT:\n{existing_content[:1500]}\n"
    )
    try:
        response = openai_chat(prompt)
        clean = response.strip().lower()
        return "duplicate" in clean
    except Exception as e:
        print(f"[AI Check Error] {e}")
        return False