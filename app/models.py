from datetime import datetime, UTC, date
from app.extensions import db, login_manager
from sqlalchemy import JSON, event
from app.utils.read_time import calculate_read_time
from slugify import slugify
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from app.utils.decorators import generate_unique_slug
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Text
import sqlalchemy as sa
from sqlalchemy import event

def generate_slug(target, value, oldvalue, initiator):
    if not value:
        return generate_unique_slug(target.title)
    return value

post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

post_labels = db.Table('post_labels',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('label.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(
        db.String(20),
        default="author"
    ) 
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
    oauth_id = db.Column(db.String(255), unique=True)
    trust_score = db.Column(db.Integer, default=0)
    is_trusted = db.Column(db.Boolean, default=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    approved_posts = db.Column(db.Integer, default=0)
    rejected_posts = db.Column(db.Integer, default=0, nullable=False)
    tokens = db.Column(db.Integer, default=5)  # starts with 5 tokens
    last_token_reset = db.Column(db.Date, default=date.today)
    daily_limit = db.Column(db.Integer, default=5)  
    _is_active = db.Column("is_active", db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    is_subscribed = db.Column(db.Boolean, default=True)
    posts = db.relationship("Post", back_populates="author", lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    # Optional: profile image, bio, etc.

    def generate_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps(self.id, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(
                token,
                salt="password-reset",
                max_age=expires_sec
            )
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
    @property
    def is_active(self):
        return self._is_active and not self.is_blocked and not self.is_deleted

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    session_id = db.Column(db.String(100), index=True)
    path = db.Column(db.String(255))
    read_time = db.Column(db.Float, default=0)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    meta_title = db.Column(db.String(160))
    meta_description = db.Column(db.String(255))
    views = db.Column(db.Integer, default=0)
    posts = db.relationship('Post', back_populates='category', lazy="dynamic")
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

@event.listens_for(Category.slug, "set", retval=True)
def receive_category_slug_set(target, value, oldvalue, initiator):
    return generate_slug(target, value, oldvalue, initiator)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    slug = db.Column(db.String(50), unique=True)
    posts = db.relationship('Post', secondary=post_tags, back_populates='tags')

@event.listens_for(Tag.slug, "set", retval=True)
def receive_category_slug_set(target, value, oldvalue, initiator):
    return generate_slug(target, value, oldvalue, initiator)

class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    posts = db.relationship(
        "Post",
        secondary=post_labels,
        back_populates="labels"
    )

class ProfileVisit(db.Model):
    __tablename__ = 'profile_visits'

    id = db.Column(db.Integer, primary_key=True)
    visited_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visitor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # nullable=True for anonymous visits
    timestamp = db.Column(db.DateTime, default=datetime.now(UTC))

    # Relationships (optional, convenient)
    visited_user = db.relationship("User", foreign_keys=[visited_user_id], backref="profile_visits_received")
    visitor = db.relationship("User", foreign_keys=[visitor_id], backref="profile_visits_made")
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def __repr__(self):
        return f"<ProfileVisit {self.visitor_id} -> {self.visited_user_id} at {self.timestamp}>"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id"),
        nullable=True
    )
    shares = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    category = db.relationship('Category', back_populates='posts')
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    related_impressions = db.Column(db.Integer, default=0)
    related_clicks = db.Column(db.Integer, default=0)
    labels = db.relationship("Label", secondary=post_labels, back_populates="posts")
    views = db.Column(db.Integer, default=0)
    status = db.Column(
        db.String(20),
        default="draft", 
        index=True
    )
    is_locked = db.Column(db.Boolean, default=False)  # ✅ add this
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    read_time = db.Column(db.Integer, default=0)  # minutes
    resubmission_count = db.Column(db.Integer, default=0)
    author = db.relationship("User", back_populates="posts")
    rejection_reason = db.Column(db.Text, nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    featured_image = db.Column(db.String(500)) 
    is_published = db.Column(db.Boolean, default=False, index=True)
    is_breaking = db.Column(db.Boolean, default=False)
    is_editor_pick = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )
    comments = db.relationship("Comment", backref="post", lazy=True)
    like_count = db.Column(db.Integer, default=0) 
    likes = db.relationship(
        "Like",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    plan = db.Column(db.String(20), default="free")

    def __repr__(self):
        return f"<Post {self.title}>"

    @property
    def daily_limit(self):
        return {
            "free": 5,
            "pro": 50,
            "newsroom": 500
        }.get(self.plan, 5)

@event.listens_for(Post.slug, "set", retval=True)
def generate_slug_on_set(target, value, oldvalue, initiator):
    if not value and value != oldvalue:
        return generate_slug(value or target.title)
    return value

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

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    privacy_policy = db.Column(db.Text, nullable=True)
    terms_conditions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.now(UTC))
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False)
    receive_digest = db.Column(db.Boolean, default=True)

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
    # "contact", "feedback", "report"

    is_read = db.Column(db.Boolean, default=False)
    is_replied = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )
    resolved = db.Column(db.Boolean, default=False)

class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    status = db.Column(db.String(50))  # sent / failed
    created_at = db.Column(db.DateTime, default=db.func.now())

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='comments')
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    replies = db.relationship('Reply', backref='comment', cascade='all, delete-orphan')

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='replies')
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))

class CommentReaction(db.Model):
    __tablename__ = "comment_reactions"

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    reaction = db.Column(db.String(20), nullable=False)  # like, love, haha, wow
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

class DailyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    date = db.Column(db.Date)
    count = db.Column(db.Integer, default=0)

class FootballCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_type = db.Column(db.String(50))  # e.g., "live", "table"
    league = db.Column(db.String(10))     # e.g., "PL"
    json_data = db.Column(db.JSON)
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC))

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class XPost(db.Model):
    __tablename__ = 'x_posts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    style = db.Column(db.String(20), default='safe')  # safe / viral / editor
    text = db.Column(db.String(280), nullable=False)
    confidence_score = db.Column(db.Integer)
    predicted_engagement = db.Column(JSONB)  # {"likes": 100, "retweets": 20, "replies": 10}
    suggested_replies = db.Column(JSONB)    # ["reply 1", "reply 2"]
    best_post_time = db.Column(TIME)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to metrics
    metrics = db.relationship('XPostMetrics', backref='x_post', lazy=True)

class XThread(db.Model):
    __tablename__ = 'x_threads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    thread = db.Column(JSONB, nullable=False)  # ["tweet1", "tweet2", ...]
    confidence_score = db.Column(db.Integer)
    predicted_engagement = db.Column(JSONB)    # {"likes": 100, "retweets": 20, "replies": 10}
    suggested_replies = db.Column(JSONB)      # ["reply 1", "reply 2"]
    best_post_time = db.Column(TIME)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class XPostMetrics(db.Model):
    __tablename__ = 'x_post_metrics'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('x_posts.id'), nullable=False)
    likes = db.Column(db.Integer, default=0)
    retweets = db.Column(db.Integer, default=0)
    replies = db.Column(db.Integer, default=0)
    engagement_score = db.Column(db.Integer)  # derived from AI + UX
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== AI Hooks for automatic analysis =====
@event.listens_for(XPost, 'before_insert')
def populate_xpost_ai_fields(mapper, connection, target):
    """
    Auto-fill AI-generated fields before inserting a new post.
    """
    from app.utils.openai_service import generate_x_post_ai, predict_engagement, suggest_replies, best_post_time_for_growth
    # Generate confidence score
    target.confidence_score = generate_x_post_ai(target.text, style=target.style, return_confidence=True)

    # Predict engagement metrics
    target.predicted_engagement = predict_engagement(target.text, target.style)

    # Suggested replies
    target.suggested_replies = suggest_replies(target.text, target.style)

    # Best post time
    target.best_post_time = best_post_time_for_growth(target.text, target.style)


@event.listens_for(XThread, 'before_insert')
def populate_xthread_ai_fields(mapper, connection, target):
    """
    Auto-fill AI-generated fields before inserting a new thread.
    """
    from app.utils.openai_service import generate_x_post_ai, predict_engagement, suggest_replies, best_post_time_for_growth
    # Generate confidence score
    target.confidence_score = generate_x_post_ai(" ".join(target.thread), style='editor', return_confidence=True)

    # Predict engagement metrics
    target.predicted_engagement = predict_engagement(" ".join(target.thread), 'editor')

    # Suggested replies
    target.suggested_replies = suggest_replies(" ".join(target.thread), 'editor')

    # Best post time
    target.best_post_time = best_post_time_for_growth(" ".join(target.thread), 'editor')

class Ad(db.Model):
    __tablename__ = "ads"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)  # optional
    target_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(50), default="sidebar")  # sidebar, header, footer, in-post
    active = db.Column(db.Boolean, default=False)  # hidden by default
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # optional for logged-in users
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    if not user_id or user_id == 'None':
        return None  #
    return User.query.get(int(user_id))