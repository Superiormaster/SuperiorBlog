# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.helper import publish_scheduled_posts
from app.utils.admin_email import send_latest_news
import atexit

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    # Use a lambda or partial to pass the app
    scheduler.add_job(
        lambda: publish_scheduled_posts(app),
        "interval",
        minutes=1,
        id="publish_scheduled_posts",
        replace_existing=True
    )
    
    scheduler.add_job(
        func=send_latest_news,
        trigger="cron",
        hour=8,
        id="send_latest_news",
        replace_existing=True
    )
    
    scheduler.start()

    # Shut down scheduler when exiting app
    atexit.register(lambda: scheduler.shutdown())