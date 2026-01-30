# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.helper import publish_scheduled_posts

scheduler = BackgroundScheduler()

def start_scheduler(app):
    # Use a lambda or partial to pass the app
    scheduler.add_job(
        lambda: publish_scheduled_posts(app),
        "interval",
        minutes=1,
        id="publish_scheduled_posts",
        replace_existing=True
    )
    scheduler.start()