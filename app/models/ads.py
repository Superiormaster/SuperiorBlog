from datetime import datetime
from app.extensions import db


class Ad(db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    target_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(50), default="sidebar") # sidebar, header, footer, in-post
    active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)