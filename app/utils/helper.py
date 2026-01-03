import os
from slugify import slugify
from werkzeug.utils import secure_filename
from flask import flash
from app.models import Tag, db

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

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file, upload_folder):
    filename = secure_filename(file.filename)
    path = os.path.join(upload_folder, filename)
    file.save(path)
    return filename

def make_slug(title):
    return slugify(title)