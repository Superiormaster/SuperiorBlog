# app/utils/openai_image.py

import os
import requests
from datetime import datetime
from app.utils.openai_caption import API_URL, HEADERS  # imported from caption file

# ---------------------------
# Low-Level Image Call
# ---------------------------

def call_ai_image(prompt, size="1024x1024", n=1):
    """
    Generate images using OpenAI Image API.
    Returns list of URLs.
    """
    if not API_URL or not HEADERS:
        print("❌ API_URL or HEADERS not configured")
        return []

    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
        "n": n
    }

    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return [img["url"] for img in data.get("data", [])]
    except Exception as e:
        print("❌ AI Image Error:", e)
        return []

# ---------------------------
# High-Level Match Image Generator
# ---------------------------

def generate_match_image(
    match_text,
    teams=None,
    event_time=None,
    recent_only=True,
    size="1024x1024"
):
    """
    Generate recent match or news visuals for X posts.

    match_text: summary or description (e.g., "Lagos FC vs Kano Pillars, 2-1")
    teams: optional tuple/list of 2 team names
    event_time: datetime of match (optional)
    recent_only: if True, focus on last 1-3 hours
    """
    time_note = ""
    if recent_only and event_time:
        time_diff = datetime.now() - event_time
        if time_diff.total_seconds() <= 10800:  # 3 hours
            time_note = "This just happened! Make it dynamic and urgent."
        else:
            time_note = "Recent match update, highlight key moments."

    team_text = ""
    if teams and len(teams) == 2:
        team_text = f"between {teams[0]} and {teams[1]}"

    prompt = f"""
Generate a high-quality, visually appealing football/news image.
{time_note}
Match: {match_text} {team_text}.
Focus on dynamic action, excitement, and engagement for social media.
Suitable for posting on X (Twitter).
"""

    return call_ai_image(prompt, size=size)