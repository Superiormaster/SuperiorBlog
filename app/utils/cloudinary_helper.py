import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from flask import current_app
import re, io
import base64
from io import BytesIO
from PIL import Image

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_image_file(file, folder="SuperiorNews", width=None, height=None, crop_for_ads=False, max_height=None):
    """
    Uploads a file object to Cloudinary.
    
    - crop_for_ads=True + width+height → Cloudinary crop (object-cover)
    - max_height → local proportional resize
    - default → upload as-is
    """
    if not file:
        current_app.logger.error("No file received")
        return None
    if not allowed_file(file.filename):
        current_app.logger.error(f"Invalid file type: {file.filename}")
        return None

    try:
        file_to_upload = file

        # If we want Cloudinary to crop for ads
        transformations = []

        if crop_for_ads and width and height:
            transformations = [{
                "width": width,
                "height": height,
                "crop": "fill",
                "gravity": "auto",
                "quality": "auto:best",
                "fetch_format": "auto"
            }]

        result = cloudinary.uploader.upload(
            file_to_upload,
            folder=folder,
            resource_type="image",
            timeout=60,
            transformation=transformations if transformations else None
        )
        return result.get("secure_url")
    except CloudinaryError as e:
        current_app.logger.error(f"Cloudinary upload failed: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
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