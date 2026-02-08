# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.helper import publish_scheduled_posts
import atexit

def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="Africa/Lagos")

    if scheduler.get_job('publish_scheduled_posts'):
        return  # already scheduled

    scheduler.add_job(
        publish_scheduled_posts,
        trigger="interval",
        minutes=1,
        id="publish_scheduled_posts",
        replace_existing=True,
        args=[app]
    )

    if not scheduler.running:
        scheduler.start()
    app.logger.info("Background scheduler started for scheduled posts.")

    # Shut down scheduler when exiting app
    atexit.register(lambda: scheduler.shutdown())