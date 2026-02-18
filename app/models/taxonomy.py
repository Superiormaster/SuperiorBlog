from datetime import datetime, UTC
from sqlalchemy import event
from app.extensions import db
from app.utils.decorators import generate_unique_slug
from .post import post_tags, post_labels


def generate_slug(target, value, oldvalue, initiator):
    if not value:
        return generate_unique_slug(target.name)
    return value


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    meta_title = db.Column(db.String(160))
    meta_description = db.Column(db.String(255))
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    posts = db.relationship("Post", back_populates="category", lazy="dynamic")


@event.listens_for(Category.slug, "set", retval=True)
def receive_category_slug_set(target, value, oldvalue, initiator):
    return generate_slug(target, value, oldvalue, initiator)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    slug = db.Column(db.String(50), unique=True)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags")


@event.listens_for(Tag.slug, "set", retval=True)
def receive_tag_slug_set(target, value, oldvalue, initiator):
    return generate_slug(target, value, oldvalue, initiator)


class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    posts = db.relationship("Post", secondary=post_labels, back_populates="labels")