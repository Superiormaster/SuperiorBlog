SPORTS_HOOKS = [
    "FULL-TIME:",
    "MATCH REPORT:",
    "JUST IN:",
    "TRANSFER UPDATE:",
    "BREAKING SPORTS NEWS:"
]

def sports_caption(text, platform):
    hook = random.choice(SPORTS_HOOKS)
    if platform.lower() == "X":
        return f"{hook} {text[:180]}"
    if platform.lower() == "Instagram":
        return f"🔥 {text}\n\n#Football #SportsNews"
    return f"{hook} {text}"

SPORTS_KEYWORDS = ["goal", "match", "league", "coach", "transfer"]

def is_sports(text):
    return any(k in text.lower() for k in SPORTS_KEYWORDS)