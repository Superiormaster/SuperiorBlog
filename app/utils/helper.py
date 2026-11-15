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

    tag_names = [
        name.strip()
        for name in raw_tags.split(",")
        if name.strip()
    ]

    if len(tag_names) > MAX_TAGS:
        flash(
            f"You can only add up to {MAX_TAGS} tags.",
            "error"
        )
        return []

    normalized_tags = {}

    for name in tag_names:
        clean_name = name.lower().replace(".", "").strip()
        slug = slugify(clean_name)

        if slug:
            normalized_tags[slug] = name

    if not normalized_tags:
        return []

    existing_tags = (
        Tag.query
        .filter(
            Tag.slug.in_(list(normalized_tags.keys()))
        )
        .all()
    )

    tags_by_slug = {
        tag.slug: tag
        for tag in existing_tags
    }

    tags = []

    for slug, name in normalized_tags.items():

        tag = tags_by_slug.get(slug)

        if not tag:
            tag = Tag(
                name=name.title(),
                slug=slug
            )

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