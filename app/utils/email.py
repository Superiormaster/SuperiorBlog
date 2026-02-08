from flask import current_app
import socket, requests, os

def send_email(to, subject, html_content, cc=None, bcc=None):
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
    sender_email = current_app.config.get("DEFAULT_EMAIL_SENDER")

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
        "htmlContent": f"""
            <div style="font-family: Arial, sans-serif;">
                {html_content}
                <br><br>
                <p>— Superior News Team</p>
            </div>
        """
    }

    if cc:
        data["cc"] = normalize(cc)
    if bcc:
        data["bcc"] = normalize(bcc)

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code in (200, 201):
            return True
        current_app.logger.error(f"Brevo email failed: {response.status_code} {response.text}")
        return False
    except Exception:
        current_app.logger.exception("Brevo email exception")
        return False