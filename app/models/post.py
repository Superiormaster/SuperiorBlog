from datetime import datetime, UTC
from sqlalchemy import JSON, event, Time
from app.extensions import db
from app.utils.read_time import calculate_read_time

# Association tables (must stay here because Post uses them)
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

post_labels = db.Table(
    'post_labels',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('label.id'), primary_key=True)
)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)

    shares = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    related_impressions = db.Column(db.Integer, default=0)
    related_clicks = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)

    status = db.Column(db.String(20), default="draft", index=True)
    is_locked = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    read_time = db.Column(db.Integer, default=0)
    resubmission_count = db.Column(db.Integer, default=0)
    rejection_reason = db.Column(db.Text, nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    featured_image = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=False, index=True)
    is_breaking = db.Column(db.Boolean, default=False)
    is_editor_pick = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    like_count = db.Column(db.Integer, default=0)
    plan = db.Column(db.String(20), default="free")

    category = db.relationship("Category", back_populates="posts")
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    labels = db.relationship("Label", secondary=post_labels, back_populates="posts")
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("Comment", backref="post", lazy=True)
    content_hash = db.Column(db.String(64), nullable=False, unique=True)
    
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post {self.title}>"

    @property
    def daily_limit(self):
        return {"free": 5, "pro": 50, "newsroom": 500}.get(self.plan, 5)


@event.listens_for(Post.content, "set", retval=False)
def update_read_time(target, value, oldvalue, initiator):
    if value:
        target.read_time = calculate_read_time(value)
    else:
        target.read_time = 0


class Repost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))


class XPost(db.Model):
    __tablename__ = "x_posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    style = db.Column(db.String(20), default="safe")
    text = db.Column(db.String(280), nullable=False)
    confidence_score = db.Column(db.Integer)
    predicted_engagement = db.Column(JSON)
    suggested_replies = db.Column(JSON)
    best_post_time = db.Column(Time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    metrics = db.relationship("XPostMetrics", backref="x_post", lazy=True)


class XThread(db.Model):
    __tablename__ = "x_threads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    thread = db.Column(JSON, nullable=False)
    confidence_score = db.Column(db.Integer)
    predicted_engagement = db.Column(JSON)
    suggested_replies = db.Column(JSON)
    best_post_time = db.Column(Time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class XPostMetrics(db.Model):
    __tablename__ = "x_post_metrics"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("x_posts.id"), nullable=False)
    likes = db.Column(db.Integer, default=0)
    retweets = db.Column(db.Integer, default=0)
    replies = db.Column(db.Integer, default=0)
    engagement_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    session_id = db.Column(db.String(100), index=True)
    path = db.Column(db.String(255))
    read_time = db.Column(db.Float, default=0)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
