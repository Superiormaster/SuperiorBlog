import os
from slugify import slugify
from flask import flash
from app.models import Tag, db
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

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

def upload_image(file):
    if not file or not allowed_file(file.filename):
        return None

    try:
      result = cloudinary.uploader.upload(
          file,
          folder="SuperiorNews",
          resource_type="image",
          timeout=60
      )
  
      return result.get("secure_url")

    except CloudinaryError as e:
        print("Cloudinary upload failed:", e)
        return None

def make_slug(title):
    return slugify(title)