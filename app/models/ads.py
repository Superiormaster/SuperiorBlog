from datetime import datetime
from sqlalchemy import Index, CheckConstraint
from app.extensions import db


class Ad(db.Model):
    __tablename__ = "ads"

    # ========================
    # Core Fields
    # ========================
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    location = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )

    type = db.Column(
        db.String(30),
        nullable=False,
        default="custom"
    )  # custom, adsense, html

    title = db.Column(
        db.String(255),
        nullable=False
    )

    image_url = db.Column(
        db.String(500),
        nullable=True
    )

    target_url = db.Column(
        db.String(500),
        nullable=False
    )

    html_code = db.Column(
        db.Text,
        nullable=True
    )

    # ========================
    # Status & Control
    # ========================
    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True
    )

    priority = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        index=True
    )

    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)

    # ========================
    # Timestamps
    # ========================
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ========================
    # Relationships
    # ========================
    impressions = db.relationship(
        "AdImpression",
        backref="ad",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    clicks = db.relationship(
        "AdClick",
        backref="ad",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ========================
    # Table Constraints
    # ========================
    __table_args__ = (
        CheckConstraint(priority >= 0, name="check_priority_positive"),
        Index("idx_ad_active_location", "active", "location"),
    )

    # ========================
    # Helper Methods
    # ========================
    def is_running(self):
        """Check if ad is currently eligible to run."""
        now = datetime.utcnow()

        if not self.active:
            return False

        if self.start_date and self.start_date > now:
            return False

        if self.end_date and self.end_date < now:
            return False

        return True

    def impression_count(self):
        return self.impressions.count()

    def click_count(self):
        return self.clicks.count()

    def ctr(self):
        """Click Through Rate"""
        impressions = self.impression_count()
        if impressions == 0:
            return 0
        return round((self.click_count() / impressions) * 100, 2)

class AdClick(db.Model):
    __tablename__ = "ad_clicks"

    id = db.Column(db.Integer, primary_key=True)

    ad_id = db.Column(
        db.Integer,
        db.ForeignKey("ads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    ip_address = db.Column(db.String(45))  # supports IPv6
    user_agent = db.Column(db.String(500))

    clicked_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    __table_args__ = (
        Index("idx_click_ad_time", "ad_id", "clicked_at"),
    )

class AdImpression(db.Model):
    __tablename__ = "ad_impressions"

    id = db.Column(db.Integer, primary_key=True)

    ad_id = db.Column(
        db.Integer,
        db.ForeignKey("ads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    __table_args__ = (
        Index("idx_impression_ad_time", "ad_id", "created_at"),
    )