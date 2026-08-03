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
    audience = db.Column(
        db.String(30),
        nullable=True,
        default="superior_news"
    )
    subscriber_id = db.Column(
      db.Integer,
      db.ForeignKey("subscriber.id"),
      nullable=True
    )
  
    subscriber = db.relationship("Subscriber")
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

class EmailCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255))   # Daily Digest July 28
    subject = db.Column(db.String(255))
    html_content = db.Column(db.Text)

    campaign_type = db.Column(db.String(20))
    # daily
    # weekly
    # draft
    # welcome
    # breaking

    status = db.Column(db.String(20), default="pending")
    # pending
    # sending
    # paused
    # completed

    batch_size = db.Column(db.Integer, default=100)
    started_at = db.Column(db.DateTime)
    paused_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    recipients = db.relationship(
        "CampaignRecipient",
        backref="campaign",
        lazy=True,
        cascade="all, delete-orphan",
    )

    total_recipients = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    completed_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

class CampaignRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey("email_campaign.id"),
        index=True,
    )
    subscriber = db.relationship(
        "Subscriber",
        backref="campaign_recipients",
    )

    subscriber_id = db.Column(
        db.Integer,
        db.ForeignKey("subscriber.id")
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    sending_started_at = db.Column(db.DateTime)
  
    email = db.Column(db.String(255), nullable=False)

    batch_number = db.Column(db.Integer, index=True)

    status = db.Column(db.String(20), default="pending", index=True)
  
    attempts = db.Column(db.Integer, default=0)
    last_attempt_at = db.Column(db.DateTime)

    sent_at = db.Column(db.DateTime)

    error = db.Column(db.Text)