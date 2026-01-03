import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app/static/uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB