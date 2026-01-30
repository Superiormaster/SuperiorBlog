# duplicate.py
from app.models import Post
from ..utils.openai_client import openai_chat

def is_duplicate(content, existing_posts):
    """
    Uses AI to check if the content is a duplicate of any existing posts.
    
    Args:
        content (str): New content to check.
        existing_posts (list[Post]): List of Post objects to compare with.
    
    Returns:
        bool: True if AI considers content duplicate.
    """
    if not existing_posts:
        return False

    # Extract text from existing posts
    existing_texts = [p.content for p in existing_posts]

    # Build AI prompt
    prompt = (
        "You are a content moderation assistant.\n"
        "Determine if the following new content is a duplicate or "
        "too similar to any of the existing content. "
        "Respond only with 'DUPLICATE' or 'UNIQUE'.\n\n"
        f"New Content:\n{content}\n\n"
        f"Existing Content:\n" + "\n---\n".join(existing_texts)
    )

    try:
        response = openai_chat(prompt)
        if not response:
            return False

        return "duplicate" in response.strip().lower()
    
    except Exception as e:
        print(f"[AI Duplicate Check] Error: {e}")
        return False


def check_post_duplicates(user_id, content):
    """
    Check for duplicates for both:
      1. Posts by the same user
      2. Posts by other users
    Returns:
        dict: { "self_duplicate": bool, "cross_user_duplicate": bool }
    """
    review_flags = {"self_duplicate": False, "cross_user_duplicate": False}

    # Get posts by same user
    user_posts = Post.query.filter_by(user_id=user_id).all()
    if is_duplicate(content, user_posts):
        review_flags["self_duplicate"] = True

    # Get posts by other users
    other_posts = Post.query.filter(Post.user_id != user_id).all()
    if is_duplicate(content, other_posts):
        review_flags["cross_user_duplicate"] = True

    return review_flags