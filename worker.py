from app import create_app
from apscheduler.schedulers.blocking import BlockingScheduler
from app.utils.admin_email import (
    send_daily_news,
    send_latest_breaking_news,
    send_weekly_digest_to_all
)

app = create_app()
scheduler = BlockingScheduler(timezone="Africa/Lagos")

def daily_jobs():
    with app.app_context():
        send_daily_news()
        send_latest_breaking_news()

def weekly_job():
    with app.app_context():
        send_weekly_digest_to_all()

# Daily at 7am
scheduler.add_job(
    daily_jobs,
    "cron",
    hour=7,
    minute=0
)

# Weekly Monday at 8am
scheduler.add_job(
    weekly_job,
    "cron",
    day_of_week="mon",
    hour=8,
    minute=0
)

print("🚀 Worker scheduler started...")
scheduler.start()