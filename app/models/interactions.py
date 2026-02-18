from datetime import datetime, UTC
from app.extensions import db


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))

    user = db.relationship("User", backref="comments")
    replies = db.relationship("Reply", backref="comment", cascade="all, delete-orphan")


class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"))

    user = db.relationship("User", backref="replies")


class CommentReaction(db.Model):
    __tablename__ = "comment_reactions"

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    reaction = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("comment_id", "user_id", name="unique_comment_reaction"),
    )

    comment = db.relationship("Comment", backref="reactions")
    user = db.relationship("User", backref="comment_reactions")


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)