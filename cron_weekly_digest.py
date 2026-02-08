#!/data/data/com.termux/files/home/Blog_App/venv/bin/python
# cron_weekly_digest.py
from app import create_app
from app.utils.admin_email import send_weekly_digest_to_all

app = create_app()

with app.app_context():
    print("Sending Weekly Digest...")
    send_weekly_digest_to_all()
    print("Weekly Digest sent ✅")