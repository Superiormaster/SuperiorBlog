import os, logging
from slugify import slugify
from flask import flash, abort, current_app
from app.models import Tag, Post
from flask_login import current_user
from functools import wraps
from datetime import datetime
from app.extensions import db

MAX_TAGS = 5

def process_tags(raw_tags):
    if not raw_tags:
        return []

    tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
    if len(tag_names) > MAX_TAGS:
        flash(f"You can only add up to {MAX_TAGS} tags.", "error")
        return []

    tags = []

    for name in tag_names:
        clean_name = name.lower().replace(".", "").strip()
        slug = slugify(clean_name)
        if not name:
          continue
        tag = Tag.query.filter_by(slug=slug).first()
        if not tag:
            tag = Tag(name=name.title(), slug=slug)
            db.session.add(tag)
        tags.append(tag)
    return tags

def make_slug(title):
    return slugify(title)

def get_related_posts(post, limit=5):
    related = []
    used_ids = {post.id}

    # 1️⃣ By tags
    if post.tags:
        tag_ids = [t.id for t in post.tags]
        tagged = (
            Post.query
            .join(Post.tags)
            .filter(
                Tag.id.in_(tag_ids),
                Post.is_published == True,
                Post.id.notin_(used_ids)
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
            .all()
        )
        related.extend(tagged)
        used_ids.update(p.id for p in tagged)

    # 2️⃣ Same category
    if len(related) < limit and post.category_id:
        cat_posts = (
            Post.query
            .filter(
                Post.category_id == post.category_id,
                Post.is_published == True,
                Post.id.notin_(used_ids)
            )
            .order_by(Post.created_at.desc())
            .limit(limit - len(related))
            .all()
        )
        related.extend(cat_posts)
        used_ids.update(p.id for p in cat_posts)

    # 3️⃣ Recent fallback
    if len(related) < limit:
        recent = (
            Post.query
            .filter(
                Post.is_published == True,
                Post.id.notin_(used_ids)
            )
            .order_by(Post.created_at.desc())
            .limit(limit - len(related))
            .all()
        )
        related.extend(recent)

    return related

logging.basicConfig(level=logging.INFO)

def publish_scheduled_posts(app):
  with app.app_context():
    now = datetime.utcnow()

    posts = Post.query.filter(
        Post.status == "scheduled",
        Post.scheduled_at <= now
    ).all()

    for post in posts:
        post.status = "published"
        post.is_published = True
        post.published_at = now
        logging.info(f"Post {post.id} published at {now}")

    if posts:
        db.session.commit()