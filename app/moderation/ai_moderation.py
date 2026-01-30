import json
from ..utils.openai_client import openai_chat

def ai_signal(text):
    prompt = f"""
Analyze this article and return JSON only:

{{
  "spam": false,
  "toxicity": 0-1,
  "quality": 0-100
}}

Article:
\"\"\"{text}\"\"\"
"""

    result = openai_chat(prompt)
    if not result:
        return {"spam": False, "toxicity": 0, "quality": 60}

    try:
        return json.loads(result)
    except:
        return {"spam": False, "toxicity": 0, "quality": 60}