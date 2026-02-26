from sqlalchemy import event
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from .post import XPost, XThread
from .user import User
from app.utils.openai_service import generate_x_post_for_user
import threading
from flask import current_app
from sqlalchemy.orm import sessionmaker

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


def run_generate_x_post(app, target_text, user_id):
    """
    Runs generate_x_post_for_user in a separate thread/session
    to avoid SQLAlchemy flush conflicts.
    """
    # Create a fresh session
    from sqlalchemy.orm import Session
    from app.extensions import db
    from app.models import XPost, XPostMetrics

    with app.app_context(): 
      SessionLocal = sessionmaker(bind=db.engine)
      session = SessionLocal()

      try:
        user = session.get(User, user_id)
        if not user:
          app.logger.warning(f"User {user_id} not found.")
          return

        result = generate_x_post_for_user(text=target_text, user=user)
    
        # Add generated posts safely in a new session
        for cap in result.get("captions", []):
          new_post = XPost(
            user_id=user.id,
            text=cap["text"],
            style=cap.get("style", "engineered"),
            confidence_score=cap.get("analysis", {}).get("hook_score", 0),
            predicted_engagement=cap.get("analysis", {}),
            suggested_replies=cap.get("suggested_replies", []),
            best_post_time=cap.get("best_post_time")
          )
          session.add(new_post)
          session.flush()
          session.add(XPostMetrics(post_id=new_post.id, engagement_score=None))
    
        session.commit()
      except Exception as e:
        session.rollback()
        app.logger.error(f"AI generation failed: {str(e)}")

      finally:
        session.close()


def start_ai_generation(target_text, user_id):
    app = current_app._get_current_object()

    threading.Thread(
        target=run_generate_x_post,
        args=(app, target_text, user_id),
        daemon=True
    ).start()


@event.listens_for(XPost, "after_insert")
def after_insert_xpost(mapper, connection, target):
    start_ai_generation(target.text, target.user_id)


@event.listens_for(XThread, "after_insert")
def after_insert_xthread(mapper, connection, target):
    full_text = " ".join(target.thread or [])
    start_ai_generation(full_text, target.user_id)