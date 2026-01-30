import re

BANNED_WORDS = [
    "scam", "betting", "crypto giveaway",
    "free money", "xxx"
]

def is_spam(content):
    content = content.lower()
    for word in BANNED_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", content):
            return True
    return False