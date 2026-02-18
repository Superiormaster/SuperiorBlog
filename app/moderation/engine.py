from .rules import CATEGORY_RULES
from .spam import is_spam
from .grammar import grammar_score
from .duplicate import check_post_duplicates
from app.models import Post
from bs4 import BeautifulSoup
import re
from flask_login import current_user
from .ai_moderation import ai_signal

MIN_GRAMMAR_SCORE = 30
def auto_moderate(post, user):
    text = BeautifulSoup(post.content, "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    word_count = len(text.split())
    grammar = grammar_score(text)
    ai = ai_signal(text)

    # ❌ Spam 🔴 HARD REJECT (ONLY THESE)
    if is_spam(text) or ai["spam"]:
        return {"status": "rejected", "reason": "Spam content detected"}
    if ai["toxicity"] > 0.8:
        return {"status": "rejected", "reason": "Harmful content"}

    review_reasons = []

    # 🟡 REVIEW QUEUE (MOST CONTENT)
    rules = CATEGORY_RULES.get(post.category.name.lower(), {"min_words": 150})
    if word_count < rules["min_words"]:
        review_reasons.append(f"Content shorter than {rules['min_words']}.")

    MIN_PARAGRAPHS = 2
    text = BeautifulSoup(post.content, "html.parser")

    # Split by double line breaks
    blocks = text.find_all(["p", "div", "section", "article"])

    # Only count blocks that contain real text
    valid_blocks = [
        b for b in blocks
        if b.get_text(strip=True)
    ]
    
    if len(valid_blocks) < MIN_PARAGRAPHS:
        review_reasons.append(
            f"Post should have at least {MIN_PARAGRAPHS} paragraphs for readability."
        )

    # ❌ Grammar too poor
    if grammar < MIN_GRAMMAR_SCORE:
        review_reasons.append("Poor grammar quality")

    # ❌ Duplicate
    duplicate_check = check_post_duplicates(
        user_id=current_user.id,
        title=post.title,
        content=text,  # or post.content if that's what you want
        category=post.category.name if post.category else None,
        post_id=post.id
    )

    if duplicate_check["exact_duplicate"]:
        return {
            "status": "rejected",
            "reason": "Exact duplicate content detected"
        }
    
    if duplicate_check["high_similarity"] or duplicate_check["ai_duplicate"]:
        review_reasons.append("Content is very similar to an existing post by another user")

    if ai["quality"] < 50:
        review_reasons.append("Low editorial quality")
    
    if review_reasons:
        return {"status": "pending_review", "reason": "; ".join(review_reasons)}

    # Always send posts to review
    return {"status": "pending_review", "reason": "Post requires editorial review"}