# cron_daily_news.py
from app import create_app
from app.utils.admin_email import send_daily_news, send_latest_breaking_news

app = create_app()

with app.app_context():
    print("Sending Daily News...")
    send_daily_news()
    print("Daily News sent ✅")

    print("Sending Breaking News...")
    send_latest_breaking_news()
    print("Breaking News sent ✅")