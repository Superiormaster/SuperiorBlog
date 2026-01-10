from flask import (
    Blueprint, render_template, request,
    redirect, current_app, url_for, flash, jsonify
)
from flask_login import (
    login_user, logout_user,
    login_required
)
from app.models import Post, Admin, AppSettings, Category, Label, Tag
from app.extensions import db, csrf
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.helper import allowed_file, process_tags, upload_image
from werkzeug.utils import secure_filename
from slugify import slugify
import os
from app.forms import LoginForm, PostForm, ChangePasswordForm

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../templates/admin"
)

# Admin login
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():  # This automatically checks POST and CSRF
        identifier = form.identifier.data  # from the WTForms field
        password = form.password.data

        # Check both username and email
        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email == identifier)
        ).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid username/email or password")
    return render_template("admin/login.html", form=form)

@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        current_password = request.form.get("current_password").strip()
        new_password = request.form.get("new_password").strip()
        confirm_password = request.form.get("confirm_password").strip()
        # Check current password
        if not check_password_hash(current_user.password, form.current_password.data):
            flash("Current password is incorrect", "error")
            return redirect(url_for("admin.change_password"))

        if form.new_password.data != form.confirm_password.data:
            flash("New passwords do not match", "error")
            return redirect(url_for("admin.change_password"))

        # Update password
        current_user.password = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/change_password.html", form=form)

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "")
    status = request.args.get("status", "all")

    query = Post.query

    if q:
        query = query.filter(Post.title.ilike(f"%{q}%"))

    if status == "published":
        query = query.filter_by(is_published=True)
    elif status == "draft":
        query = query.filter_by(is_published=False)

    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=6)

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        q=q,
        status=status
    )

@admin_bp.route("/create", methods=["GET", "POST"])
@admin_bp.route("/post/<int:id>/edit", methods=["GET", "POST"])
@login_required
def create_or_edit(id=None):
    post = Post.query.get(id) if id else None
    categories = Category.query.all()
    labels = Label.query.all()
    tags = Tag.query.order_by(Tag.name.asc()).all()

    form = PostForm(obj=post)

    # 🔹 IMPORTANT: choices MUST be set before validate
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    form.labels.choices = [(l.id, l.name) for l in Label.query.all()]

    # 🔹 Preselect relations on edit
    if post and request.method == "GET":
        form.category.data = post.category_id
        form.labels.data = [l.id for l in post.labels]

    if form.validate_on_submit():
        submit_type = request.form.get("submit_type")

        title = form.title.data
        content = form.content.data
        is_published = submit_type == "publish"

        if not title or not content:
            flash("Title and content are required", "error")
            return redirect(url_for("admin.create"))

        if not post:
            post = Post()
            db.session.add(post)

        post.title = form.title.data
        post.slug = slugify(post.title)
        post.content = form.content.data
        post.is_published = is_published

        category = Category.query.get(form.category.data)
        if not category:
            flash("Invalid category selected", "danger")
            return redirect(request.url)
        post.category = category

        # Labels
        post.labels = Label.query.filter(
            Label.id.in_(form.labels.data)
        ).all()

        # Tags
        raw_tags = request.form.get("tags", "")
        post.tags.clear()
        post.tags.extend(process_tags(raw_tags))

        # Image upload
        image_file = form.image.data
        if image_file:
          image_url = upload_image(image_file)
          if image_url:
            post.featured_image = image_url
          else:
            flash("Image upload failed. Post saved without image.", "error")
            print("IMAGE FILE:", image_file)
            print("FILENAME:", getattr(image_file, "filename", None))

        db.session.commit()

        flash(
            "Post published successfully" if is_published else "Draft saved successfully",
            "success"
        )

        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/create.html",
        form=form,
        post=post,
        existing_tags=[t.name for t in post.tags] if post else []
    )

@admin_bp.route("/tags")
@login_required
def tags():
    tags = (
        db.session.query(
            Tag,
            db.func.count(Post.id).label("post_count")
        )
        .outerjoin(Tag.posts)
        .group_by(Tag.id)
        .order_by(Tag.name.asc())
        .all()
    )

    return render_template("admin/tags.html", tags=tags)

@admin_bp.route("/tags/search")
@login_required
def search_tags():
    q = request.args.get("q", "").strip()

    if not q or len(q) < 2:
        return jsonify([])

    tags = (
        Tag.query
        .filter(Tag.name.ilike(f"%{q}%"))
        .order_by(Tag.name.asc())
        .limit(10)
        .all()
    )

    return jsonify([
        {"id": tag.id, "name": tag.name}
        for tag in tags
    ])

@admin_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
def delete(id):
    post = Post.query.get_or_404(id)

    db.session.delete(post)
    db.session.commit()

    flash("Post deleted", "success")
    return redirect(url_for("admin.dashboard"))
    
@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("admin.login"))
    
@admin_bp.route("/toggle_publish/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
def toggle_publish(id):
    post = Post.query.get_or_404(id)
    post.is_published = not post.is_published
    db.session.commit()

    flash(f"Post {'published' if post.is_published else 'unpublished'}", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = AppSettings.query.first()
    if not settings:
        settings = AppSettings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == "POST":
        settings.privacy_policy = request.form.get("privacy_policy")
        settings.terms_conditions = request.form.get("terms_conditions")
        db.session.commit()
        flash("Settings updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/settings.html", settings=settings)