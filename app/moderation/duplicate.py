from app.models import Post
import hashlib
from difflib import SequenceMatcher
from ..utils.openai_client import openai_chat


SIMILARITY_THRESHOLD = 0.90
AI_THRESHOLD_LOW = 0.75
AI_THRESHOLD_HIGH = 0.89

MAX_DUPLICATE_CANDIDATES = 20


def hash_content(text: str) -> str:
    """Generate a SHA256 hash of the content."""

    if not isinstance(text, str):
        text = ""

    text = text.strip().lower()

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


def check_post_duplicates(
    user_id: int,
    title: str,
    content: str,
    category=None,
    post_id=None
):
    """
    Checks for duplicate content against the 20 most recent
    non-rejected posts.

    Rejected posts are excluded.

    Returns:
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

    # 1. Exact duplicate check.
    # Retrieve only the ID.

    content_hash = hash_content(content)

    exact_query = (
        Post.query
        .with_entities(Post.id)
        .filter(
            Post.content_hash == content_hash,
            Post.status != "rejected"
        )
    )

    if post_id is not None:
        exact_query = exact_query.filter(
            Post.id != post_id
        )

    if exact_query.first():
        review_flags["exact_duplicate"] = True
        return review_flags

    # 2. Retrieve only the fields required for comparison.

    query = Post.query.filter(
        Post.status != "rejected"
    )

    # Filter by category when available.

    if category is not None:

        if hasattr(category, "id"):
            category_id = category.id

        elif isinstance(category, int):
            category_id = category

        else:
            category_id = None

        if category_id is not None:
            query = query.filter(
                Post.category_id == category_id
            )

    # Exclude the current post when editing.

    if post_id is not None:
        query = query.filter(
            Post.id != post_id
        )

    existing_posts = (
        query
        .with_entities(
            Post.title,
            Post.content
        )
        .order_by(
            Post.id.desc()
        )
        .limit(MAX_DUPLICATE_CANDIDATES)
        .all()
    )

    # 3. Compare titles and content.

    for existing_title, existing_content in existing_posts:

        title_score = similarity(
            title,
            existing_title
        )

        if title_score >= SIMILARITY_THRESHOLD:
            review_flags["high_similarity"] = True

        content_score = similarity(
            content,
            existing_content
        )

        if content_score >= SIMILARITY_THRESHOLD:
            review_flags["high_similarity"] = True

        elif (
            AI_THRESHOLD_LOW
            <= content_score
            <= AI_THRESHOLD_HIGH
        ):
            ai_result = ai_check_duplicate(
                content,
                existing_content
            )

            if ai_result:
                review_flags["ai_duplicate"] = True

        # Stop when a duplicate has already been established.

        if (
            review_flags["high_similarity"]
            or review_flags["ai_duplicate"]
        ):
            break

    return review_flags


def ai_check_duplicate(
    new_content: str,
    existing_content: str
) -> bool:
    """
    Calls OpenAI to check semantic similarity.
    """

    prompt = (
        "You are a content moderation assistant. "
        "Determine if the NEW content is semantically the same story "
        "as the EXISTING content. "
        "Respond ONLY with DUPLICATE or UNIQUE.\n\n"
        f"NEW CONTENT:\n{new_content[:1500]}\n\n"
        f"EXISTING CONTENT:\n{existing_content[:1500]}\n"
    )

    try:
        response = openai_chat(prompt)
        clean = response.strip().lower()

        return "duplicate" in clean

    except Exception:
        return False