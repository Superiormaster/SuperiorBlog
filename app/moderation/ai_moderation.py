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
        start = result.find("{")
        end = result.rfind("}") + 1
        clean = result[start:end]
        return json.loads(clean)
    except Exception as e:
        print("AI JSON ERROR:", e)
        print("RAW AI RESPONSE:", result)
        return {"spam": False, "toxicity": 0, "quality": 60}