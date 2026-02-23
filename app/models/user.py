from datetime import datetime, date, UTC
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from app.extensions import db
from app.utils.decorators import generate_unique_slug
from .post import Post
import secrets

def generate_slug(target, value, oldvalue, initiator):
    if not value:
        return generate_unique_slug(target.title)
    return value

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), default="author")
    is_admin = db.Column(db.Boolean, default=False)
    profile_visits = db.Column(db.Integer, default=0)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)
    profile_completed = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(120))
    location = db.Column(db.String(50))
    description = db.Column(db.Text)
    category = db.Column(db.String(80))
    phone = db.Column(db.String(30))
    id_number = db.Column(db.String(30))
    id_type = db.Column(db.String(50))
    bank_account = db.Column(db.String(50))
    referral_link = db.Column(db.String(255))
    oauth_provider = db.Column(db.String(50))
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    oauth_id = db.Column(db.String(255), unique=True)
    trust_score = db.Column(db.Integer, default=0)
    is_trusted = db.Column(db.Boolean, default=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    approved_posts = db.Column(db.Integer, default=0)
    rejected_posts = db.Column(db.Integer, default=0, nullable=False)
    tokens = db.Column(db.Integer, default=5)
    last_token_reset = db.Column(db.Date, default=date.today)
    daily_limit = db.Column(db.Integer, default=5)
    _is_active = db.Column("is_active", db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    is_subscribed = db.Column(db.Boolean, default=True)
    posts = db.relationship("Post", back_populates="author", lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def generate_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps(self.id, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token, salt="password-reset", max_age=expires_sec)
        except Exception:
            return None
        return User.query.get(user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    @is_active.setter
    def is_active(self, value):
        self._is_active = value


class ProfileVisit(db.Model):
    __tablename__ = 'profile_visits'
    id = db.Column(db.Integer, primary_key=True)
    visited_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visitor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now(UTC))
    visited_user = db.relationship("User", foreign_keys=[visited_user_id], backref="profile_visits_received")
    visitor = db.relationship("User", foreign_keys=[visitor_id], backref="profile_visits_made")
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def __repr__(self):
        return f"<ProfileVisit {self.visitor_id} -> {self.visited_user_id} at {self.timestamp}>"


class DailyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    date = db.Column(db.Date)
    count = db.Column(db.Integer, default=0)


class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.now(UTC))
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_hex(32))
    receive_digest = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    last_email_sent = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='subscriber', uselist=False)