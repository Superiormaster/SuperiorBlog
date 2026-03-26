import os, json
from dotenv import load_dotenv
import cloudinary
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Cookie works across HTTPS & all pages
    SESSION_COOKIE_DOMAIN = ".superiornews.app"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None"

    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_MONTHLY_PLAN = os.getenv("PAYSTACK_MONTHLY_PLAN")
    PAYSTACK_YEARLY_PLAN = os.getenv("PAYSTACK_YEARLY_PLAN")
    PAYSTACK_BASE_URL = "https://api.paystack.co"
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Brevo / Sendinblue
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    EMAIL_PROVIDER = "brevo"
    DEFAULT_EMAIL_SENDER = os.getenv("DEFAULT_EMAIL_SENDER", "noreply@superiornews.app")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)