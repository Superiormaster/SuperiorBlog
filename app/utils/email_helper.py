import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_FROM_EMAIL = os.getenv("MAILGUN_FROM_EMAIL")
MAILGUN_TO_EMAIL = os.getenv("MAILGUN_TO_EMAIL")


def send_mailgun_email(subject: str, text: str, to_email: str = MAILGUN_TO_EMAIL):
    """
    Sends an email via Mailgun.
    """
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": MAILGUN_FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "text": text,
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print("Mailgun error:", e)
        return False