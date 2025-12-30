from flask import (
    Blueprint, render_template, request,
    redirect, current_app, url_for, flash, jsonify
)
from flask_login import (
    login_user, logout_user,
    login_required
)
from app.models import Post, Admin, AppSettings, Category, Label
from app.extensions import db
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils import allowed_file
from werkzeug.utils import secure_filename
from slugify import slugify
import os

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../templates/admin"
)

#Admin login
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid username or password")
    return render_template("admin/login.html")

@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password").strip()
        new_password = request.form.get("new_password").strip()
        confirm_password = request.form.get("confirm_password").strip()

        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect", "error")
            return redirect(url_for("admin.change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match", "error")
            return redirect(url_for("admin.change_password"))

        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("Password updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/change_password.html")

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
def create():
    categories = Category.query.all()
    labels = Label.query.all()
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")

        if not title or not content:
            flash("Title and content are required", "error")
            return redirect(url_for("admin.create"))

        is_published = bool(request.form.get('is_published'))

        slug = slugify(title)

        # 🔹 CATEGORY
        category_id = request.form.get("category")
        category = Category.query.get(category_id)

        if not category:
            flash("Invalid category selected", "danger")
            return redirect(request.url)

        # 🔹 LABELS
        label_ids = request.form.getlist("labels")
        post_labels = Label.query.filter(
            Label.id.in_(label_ids)
        ).all()

        label = request.form.get("label")

        # Create the post first
        post = Post(title=title, slug=slug, content=content, is_published=is_published, category=category, label=label)

        post.labels = post_labels   # ✅ list of model instances

        for label_id in label_ids:
            label = Label.query.get(label_id)
            if label:
                post.labels.append(label)

        # Handle file upload
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            post.featured_image = filename  # ✅ now post exists

        db.session.add(post)
        db.session.commit()

        flash("Post created successfully", "success")
        return redirect(url_for("public.index"))

    return render_template("admin/create.html", categories=categories, labels=labels, post=None)

@admin_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    categories = Category.query.all()
    labels = Label.query.all()
    
    file = request.files.get("image")

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        post.featured_image = filename

    if request.method == "POST":
        post.title = request.form.get("title")
        post.content = request.form.get("content")
        post.slug = slugify(post.title)
        post.is_published = bool(request.form.get("is_published"))

        db.session.commit()

        flash("Post updated", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/create.html", post=post, categories=categories, labels=labels)
    
@admin_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
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
def toggle_publish(id):
    post = Post.query.get_or_404(id)
    post.is_published = not post.is_published
    db.session.commit()
    return jsonify({
        "status": "published" if post.is_published else "draft"
    })
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