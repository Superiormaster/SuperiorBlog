from flask import current_app
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def send_email(to, subject, html_content, text_content=None, cc=None, bcc=None):
    """
    Send email using Brevo API (formerly Sendinblue)
    
    Parameters:
    - to: str or list[str] → primary recipients
    - subject: str → email subject
    - html_content: str → HTML content of the email
    - cc: optional list[str] → CC recipients
    - bcc: optional list[str] → BCC recipients
    """

    url = "https://api.brevo.com/v3/smtp/email"
    api_key = current_app.config.get("BREVO_API_KEY")
    print(api_key[:10] + "..." if api_key else "No key loaded")
    sender_email = current_app.config.get("DEFAULT_EMAIL_SENDER")
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
  
    adapter = HTTPAdapter(max_retries=retry)
  
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if not api_key or not sender_email:
        current_app.logger.error("BREVO_API_KEY or DEFAULT_EMAIL_SENDER is missing")
        return False

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    # Helper to normalize recipients into Brevo format
    def normalize(emails):
        if not emails:
            return None
        if isinstance(emails, str):
            emails = [emails]
        return [{"email": e} for e in emails]

    data = {
        "sender": {"name": "Superior News", "email": sender_email},
        "to": normalize(to),
        "subject": subject,
        "htmlContent": html_content
    }
  
    if text_content:
      data["textContent"] = text_content

    if cc:
        data["cc"] = normalize(cc)
    if bcc:
        data["bcc"] = normalize(bcc)

    try:
        response = session.post(
          url,
          json=data,
          headers=headers,
          timeout=(10, 30),
        )
        if response.status_code in (200, 201):
            return {
                "success": True,
                "temporary": False,
                "error": None,
            }
        
        if response.status_code == 400:
            return {
                "success": False,
                "temporary": False,
                "error": "Invalid recipient",
            }
        
        if response.status_code == 401:
            return {
                "success": False,
                "temporary": False,
                "error": "Unauthorized",
            }
        
        if response.status_code == 429:
            return {
                "success": False,
                "temporary": True,
                "error": "Rate limited",
            }
        
        if response.status_code >= 500:
            return {
                "success": False,
                "temporary": True,
                "error": "Brevo server error",
            }
        
        return {
            "success": False,
            "temporary": False,
            "error": response.text,
        }
  
    except requests.exceptions.Timeout:
        current_app.logger.exception("Brevo timeout")
        return {
          "success": False,
          "temporary": True,
          "error": "Connection timeout",
        }
  
    except requests.exceptions.ConnectionError:
        current_app.logger.exception("Brevo connection error")
        return {
          "success": False,
          "temporary": True,
          "error": "Network unavailable",
        }
  
    except requests.exceptions.SSLError:
        current_app.logger.exception("Brevo SSL error")
        return {
            "success": False,
            "temporary": True,
            "error": "Brevo SSL error",
        }
  
    except Exception:
        current_app.logger.exception("Brevo email exception")
        return {
            "success": False,
            "temporary": True,
            "error": "Brevo email exception",
        }