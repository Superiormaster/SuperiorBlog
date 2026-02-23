from datetime import datetime, UTC
from app.extensions import db


class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    privacy_policy = db.Column(db.Text, nullable=True)
    terms_conditions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))


class DigestDraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    is_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))


class BreakingNews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    published_at = db.Column(db.DateTime, default=datetime.now(UTC))


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    message = db.Column(db.Text)
    subject = db.Column(db.String(200), nullable=True)
    type = db.Column(db.String(20))
    is_read = db.Column(db.Boolean, default=False)
    is_replied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    resolved = db.Column(db.Boolean, default=False)


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(
        db.Integer,
        db.ForeignKey('subscriber.id',
        name='fk_emaillog_subscriber_id'),
        nullable=True
    )
    status = db.Column(db.String(50))
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    subscriber = db.relationship("Subscriber", backref="email_logs")

    def __repr__(self):
        return f"<EmailLog {self.email} - {self.subject}>"


class FootballCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_type = db.Column(db.String(50))
    league = db.Column(db.String(10))
    json_data = db.Column(db.JSON)
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC))


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="pending")
    subscription_code = db.Column(db.String(120))
    customer_code = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
