import re

WORDS_PER_MINUTE = 200

def calculate_read_time(html: str) -> int:
    if not html:
        return 1

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)

    # Normalize spaces
    words = len(text.split())

    return max(1, round(words / WORDS_PER_MINUTE))