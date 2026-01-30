import re

def grammar_score(text):
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 3]

    if not sentences:
        return 0

    capitalized = sum(1 for s in sentences if s[0].isupper())
    base = (capitalized / len(sentences)) * 100

    avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
    if avg_length > 8:
        base += 10  # add a small bonus

    return min(int(base), 100)