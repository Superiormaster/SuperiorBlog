from flask import current_app
from flask_mail import Message as MailMessage
from app.extensions import mail
import socket

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