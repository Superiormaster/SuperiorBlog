from .rules import CATEGORY_RULES
from .spam import is_spam
from .grammar import grammar_score
from .duplicate import is_duplicate, check_post_duplicates
from app.models import Post
from bs4 import BeautifulSoup
import re
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

    # ❌ Grammar too poor
    if grammar < MIN_GRAMMAR_SCORE:
        return {
            "status": "rejected",
            "reason": "Poor grammar quality, Needs editing"
        }

    # ❌ Duplicate
    duplicate_check = check_post_duplicates(user.id, text)
    if duplicate_check["self_duplicate"]:
        review_reasons.append("Possible duplicate content detected")
    
    if duplicate_check["cross_user_duplicate"]:
        review_reasons.append("Content is very similar to existing post by another user")

    if ai["quality"] < 50:
        review_reasons.append("Low editorial quality")
    
    if review_reasons:
        return {"status": "pending_review", "reason": "; ".join(review_reasons)}

    # ✅ Passed moderation
    return {
        "status": "approved",
        "reason": None,
    }