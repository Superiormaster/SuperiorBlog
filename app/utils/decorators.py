from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def generate_unique_slug(title):
    import re, unicodedata
    from app.models import Post
    """
    Generate a unique slug for a post based on the title.
    """
    # Convert title to ASCII, lowercase, replace spaces with dashes
    slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii').lower()).strip('-')
    
    # Check if slug already exists
    existing = Post.query.filter_by(slug=slug).first()
    counter = 1
    new_slug = slug
    while existing:
        new_slug = f"{slug}-{counter}"
        existing = Post.query.filter_by(slug=new_slug).first()
        counter += 1

    return new_slug

def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please login as admin", "danger")
            return redirect(url_for("admin.login"))

        # Ensure user is Admin model
        if current_user.__class__.__name__ != "Admin":
            flash("Not admin", "danger")
            return redirect(url_for("admin.login"))

        return view_func(*args, **kwargs)
    return wrapped

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in.", "danger")
                return redirect(url_for("admin.login"))

            # If using role column
            if not hasattr(current_user, "role"):
                flash("Access denied.", "danger")
                return redirect(url_for("admin.login"))

            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("public.index"))

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator