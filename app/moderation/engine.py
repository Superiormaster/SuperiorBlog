from .rules import CATEGORY_RULES
from .spam import is_spam
from .grammar import grammar_score
from .duplicate import check_post_duplicates
from .ai_moderation import ai_signal

from bs4 import BeautifulSoup
import re


MIN_GRAMMAR_SCORE = 30
MIN_PARAGRAPHS = 2


def auto_moderate(post, user):

    html_soup = BeautifulSoup(
        post.content or "",
        "html.parser"
    )

    text = html_soup.get_text(" ")

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    word_count = len(text.split())

    grammar = grammar_score(text)

    ai = ai_signal(text) or {}

    spam = ai.get("spam", False)
    toxicity = ai.get("toxicity", 0)
    quality = ai.get("quality", 50)

    # Hard rejection: spam
    if is_spam(text) or spam:
        return {
            "status": "rejected",
            "reason": "Spam content detected"
        }

    # Hard rejection: harmful content
    if toxicity > 0.8:
        return {
            "status": "rejected",
            "reason": "Harmful content"
        }

    review_reasons = []

    category_name = (
        post.category.name.lower()
        if post.category
        else "uncategorized"
    )

    rules = CATEGORY_RULES.get(
        category_name,
        {"min_words": 150}
    )

    min_words = rules.get("min_words", 150)

    if word_count < min_words:
        review_reasons.append(
            f"Content shorter than {min_words}."
        )

    # Paragraph validation
    blocks = html_soup.find_all(
        ["p", "div", "section", "article"]
    )

    valid_blocks = [
        block
        for block in blocks
        if block.get_text(strip=True)
    ]

    if len(valid_blocks) < MIN_PARAGRAPHS:
        review_reasons.append(
            "Post should have at least "
            f"{MIN_PARAGRAPHS} paragraphs for readability."
        )

    # Grammar validation
    if grammar < MIN_GRAMMAR_SCORE:
        review_reasons.append(
            "Poor grammar quality"
        )

    # Duplicate detection
    duplicate_check = check_post_duplicates(
        user_id=user.id,
        title=post.title,
        content=text,
        category=post.category_id,
        post_id=post.id
    )

    if duplicate_check.get("exact_duplicate"):
        return {
            "status": "rejected",
            "reason": "Exact duplicate content detected"
        }

    if (
        duplicate_check.get("high_similarity")
        or duplicate_check.get("ai_duplicate")
    ):
        review_reasons.append(
            "Content is very similar to an existing post by another user"
        )

    if quality < 50:
        review_reasons.append(
            "Low editorial quality"
        )

    if review_reasons:
        return {
            "status": "pending_review",
            "reason": "; ".join(review_reasons)
        }

    return {
        "status": "pending_review",
        "reason": "Post requires editorial review"
    }