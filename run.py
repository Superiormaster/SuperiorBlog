import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.scheduler import start_scheduler

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
from app import create_app

app = create_app()
if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("FLASK_RUN_FROM_CLI"):
    start_scheduler(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)