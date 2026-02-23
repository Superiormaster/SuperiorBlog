from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.scheduler import start_scheduler

app = create_app()
start_scheduler(app)