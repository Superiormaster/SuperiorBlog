from datetime import datetime 
from app.extensions import db, login_manager
from sqlalchemy import JSON
from slugify import slugify
from flask_login import UserMixin
from sqlalchemy import event
from werkzeug.security import check_password_hash, generate_password_hash

def generate_slug(target, value, oldvalue, initiator):
    if not value:
        return slugify(target.name)
    return value

post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

post_labels = db.Table('post_labels',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
    db.Column('label_id', db.Integer, db.ForeignKey('label.id'))
)

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    meta_title = db.Column(db.String(160))
    meta_description = db.Column(db.String(255))
    views = db.Column(db.Integer, default=0)
    posts = db.relationship('Post', back_populates='category', lazy="dynamic")

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

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id"),
        nullable=True
    )
    category = db.relationship('Category', back_populates='posts')
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    label = db.Column(db.String(50)) 
    labels = db.relationship("Label", secondary=post_labels, back_populates="posts")
    views = db.Column(db.Integer, default=0)
    featured_image = db.Column(db.String(255)) 
    is_published = db.Column(db.Boolean, default=False)
    is_breaking = db.Column(db.Boolean, default=False)
    is_editor_pick = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    comments = db.relationship("Comment", backref="post", lazy=True)
    likes = db.relationship(
        "Like",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Post {self.title}>"

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    privacy_policy = db.Column(db.Text, nullable=True)
    terms_conditions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    resolved = db.Column(db.Boolean, default=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))