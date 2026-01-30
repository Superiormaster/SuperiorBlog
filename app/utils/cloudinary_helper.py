import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from flask import current_app
import re
import base64
from io import BytesIO

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image_file(file, folder="SuperiorNews"):
    """
    Uploads a normal file object (from <input type="file">)
    """
    if not file:
        current_app.logger.error("No file received")
        return None
    if not allowed_file(file.filename):
        current_app.logger.error(f"Invalid file type: {file.filename}")
        return None

    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image",
            timeout=60
        )
        return result.get("secure_url")
    except CloudinaryError as e:
        current_app.logger.error(f"Cloudinary upload failed: {e}")
        return None


def upload_base64_image(base64_str, folder="SuperiorNews"):
    """
    Uploads a base64 image string and returns Cloudinary URL
    """
    try:
        result = cloudinary.uploader.upload(
            base64_str,
            folder=folder,
            resource_type="image",
            timeout=60
        )
        return result.get("secure_url")
    except CloudinaryError as e:
        current_app.logger.error(f"Cloudinary base64 upload failed: {e}")
        return None