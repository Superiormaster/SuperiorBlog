from flask import current_app
from flask_mail import Message as MailMessage
from app.extensions import mail
import socket, requests, os

def send_email(to, subject, body, html=None):
  try:
    msg = MailMessage(
        subject=subject,
        recipients=[to],
        sender=current_app.config["MAIL_DEFAULT_SENDER"]
    )

    if html:
        msg.html = html
    else:
        msg.body = body

    mail.send(msg)
    return True
  
  except (OSError, socket.error) as e:
    current_app.logger.error(f"Email send failed: {e}")
    return False

  except Exception as e:
    current_app.logger.exception("Unexpected email error")
    return False

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

def send_bulk_email(to, subject, html):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "sender": {"name": "Superior News", "email": "noreply@superiornews.app"},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html
    }

    requests.post(url, json=data, headers=headers)

def send_weekly_digest(subscriber, posts):
    items = "".join([
        f"<li><a href='https://superiornews/public/post/{p.slug}'>{p.title}</a><p>{p.excerpt}</p></li>"
        for p in posts
    ])
    html = f"""
    <h2>This Week on Superior Blog</h2>
    <ul>{items}</ul>
    <p><a href='https://superiornews.app/public/user_login'>Start Writing</a></p>
    <p style='font-size:12px'>
        <a href='https://superiornews/public/unsubscribe/{subscriber.unsubscribe_token}'>Unsubscribe</a>
    </p>
    """
    send_bulk_email(subscriber.email, "Weekly Digest", html)