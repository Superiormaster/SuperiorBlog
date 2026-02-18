from sqlalchemy import event
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from .post import XPost, XThread


class CaptionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    input_text = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Integer)
    tone = db.Column(db.String(50))
    caption = db.Column(db.Text, nullable=False)
    length = db.Column(db.String(50))
    platform = db.Column(db.String(50))
    captions = db.Column(db.JSON)
    style = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.now())


@event.listens_for(XPost, "before_insert")
def populate_xpost_ai_fields(mapper, connection, target):
    from app.utils.openai_service import (
        generate_x_post_ai,
        predict_engagement,
        suggest_replies,
        best_post_time_for_growth,
    )

    target.confidence_score = generate_x_post_ai(
        target.text, style=target.style, return_confidence=True
    )
    target.predicted_engagement = predict_engagement(target.text, target.style)
    target.suggested_replies = suggest_replies(target.text, target.style)
    target.best_post_time = best_post_time_for_growth(target.text, target.style)


@event.listens_for(XThread, "before_insert")
def populate_xthread_ai_fields(mapper, connection, target):
    from app.utils.openai_service import (
        generate_x_post_ai,
        predict_engagement,
        suggest_replies,
        best_post_time_for_growth,
    )

    full_text = " ".join(target.thread)

    target.confidence_score = generate_x_post_ai(
        full_text, style="editor", return_confidence=True
    )
    target.predicted_engagement = predict_engagement(full_text, "editor")
    target.suggested_replies = suggest_replies(full_text, "editor")
    target.best_post_time = best_post_time_for_growth(full_text, "editor")