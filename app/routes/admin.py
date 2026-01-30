from flask import (
    Blueprint, render_template, request,
    redirect, current_app, url_for, flash, jsonify
)
from datetime import datetime
from flask_login import (
    login_user, logout_user,
    login_required
)
from flask_mail import Message as MailMessage
from app.utils.decorators import admin_required, role_required
from app.utils.db_helpers import safe_commit
from app.utils.email import send_email
from app.moderation.engine import auto_moderate
from app.models import Post, Admin, AppSettings, Category, Label, Tag, CaptionHistory, User, Comment, ContactMessage, Repost
from app.extensions import db, csrf, mail
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.analytics import analytics_block
from sqlalchemy import func
from app.utils.cloudinary_helper import upload_image_file
from app.utils.helper import process_tags
from werkzeug.utils import secure_filename
from slugify import slugify
import os
from app.forms import LoginForm, PostForm, ChangePasswordForm, PrivacyTermsForm

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

    if form.validate_on_submit():
        identifier = form.identifier.data
        password = form.password.data

        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email == identifier)
        ).first()

        if not admin or not admin.check_password(password):
            flash("Invalid username/email or password", "danger")
            return redirect(url_for("admin.login"))

        login_user(admin)
        flash("Welcome Admin", "success")
        return redirect(url_for("admin.dashboard"))

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
        if not safe_commit():
          print("Failed to change password")
        flash("Password updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/change_password.html", form=form)

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all").lower()

    # Start query with all posts
    query = Post.query

    # Search by title if query provided
    if q:
        query = query.filter(Post.title.ilike(f"%{q}%"))

    # Filter by status if not "all"
    if status == "published":
        query = query.filter_by(status="published")
    elif status == "draft":
        query = query.filter_by(status="draft")
    elif status == "pending":
        query = query.filter_by(status="pending")
    elif status == "rejected":
        query = query.filter_by(status="rejected")

    # Order by newest first
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=10)

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        q=q,
        status=status
    )

@admin_bp.route("/post/create", methods=["GET", "POST"], endpoint='create_post')
@login_required
def create():
    return create_or_edit()
@admin_bp.route("/post/<int:id>/edit", methods=["GET", "POST"], endpoint='edit_post')
@login_required
def edit(id):
    return create_or_edit(id)

def create_or_edit(id=None):
    # Fetch post if editing, else create new
    post = Post.query.get(id) if id else None
    form = PostForm(obj=post or None)

    status = None
    reason = None

    # ---- Moderation / category rules (SAFE & CLEAN) ----
    rules = {
        "min_words": 150,
        "good_grammar_score": 60,
        "avoid_words": []
    }
    
    if post and post.category:
        category_key = post.category.name.lower()
        category_rules = CATEGORY_RULES.get(category_key, {})
    
        rules.update({
            "min_words": category_rules.get("min_words", 150),
            "avoid_words": category_rules.get("avoid_words", [])
        })

    if id and not post:
        flash("Post not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    # 🔐 Ownership check for editing
    if post and post.id and post.user_id != current_user.id:
        flash("You are not allowed to edit this post.", "danger")
        return redirect(url_for("admin.dashboard"))

    # Block editing if published
    if post and post.status == "published":
        flash("Published posts cannot be edited.", "warning")
        return redirect(url_for("admin.dashboard"))

    # Block if rejected but max resubmissions reached
    if post and post.status == "rejected" and (post.resubmission_count or 0) >= 2:
        flash("Maximum resubmissions reached.", "danger")
        return redirect(url_for("admin.dashboard"))

    # Set choices for category and labels
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    form.labels.choices = [(l.id, l.name) for l in Label.query.all()]

    # Pre-fill form on GET
    if request.method == "GET" and post:
        form.category.data = post.category_id
        form.labels.data = [l.id for l in post.labels]

    guidelines = rules

    if form.validate_on_submit():
        is_new = False
  
        featured_image = request.form.get("featured_image")
        content_html = request.form.get("content", "")
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator=" ").strip()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        word_count = len(text.split())
        
        if word_count < rules.get("min_words", 150):
            flash(f"Post must have at least {rules['min_words']} words", "danger")
            return render_template("user/create.html", form=form, rules=rules, post=post)

        if not post:
            is_new = True
            # Check if title is empty
            if not form.title.data or not form.title.data.strip():
                flash("Please enter a title before saving.", "error")
                return redirect(request.referrer)

            # Creating new post
            post = Post(
                user_id=current_user.id,
                title=form.title.data,
                content=content_html.strip(),
                featured_image=featured_image,
                slug=generate_unique_slug(form.title.data),
                resubmission_count=0,
                status="draft",
                is_published=False
            )
        else:
            # Editing existing post
            post.title = form.title.data
            post.content = content_html.strip()
            post.featured_image = request.form.get("featured_image")
            # Only increment resubmission count if rejected
            if post.status == "rejected":
                post.resubmission_count = (post.resubmission_count or 0) + 1
                post.status = "draft"
                post.is_published = False

        # Assign category
        category = Category.query.get(form.category.data)
        if not category:
            flash("Invalid category selected", "danger")
            return redirect(request.url)
        post.category = category

        # Assign labels
        post.labels = Label.query.filter(Label.id.in_(form.labels.data)).all()

        # Assign tags
        raw_tags = request.form.get("tags", "")
        post.tags = process_tags(raw_tags)

        if not text:
            flash("Post content cannot be empty.", "danger")
            return render_template("admin/create.html", form=form, rules=rules, post=post)

        db.session.add(post)
        if not safe_commit():
          print("Failed to save post")

        # Make sure you correct this especially looking at grammar.py
        try:
          result = auto_moderate(post, current_user) if post else None
          status = result["status"]
          reason = result.get("reason")
  
          if status == "rejected":
              post.status = "rejected"
              flash(reason, "error")
              if not safe_commit():
                print("Post rejected.")
              return redirect(url_for("admin.edit_post", id=post.id))
          
          if status == "pending_review":
              post.status = "pending_review"
              flash(reason or "Post requires editorial review", "warning")
              if not safe_commit():
                print("Post in pending review")
              return redirect(url_for("admin.dashboard"))
          # ✅ Auto-approve
          post.status = "approved"
          post.is_published = False
        except ConnectionError:
          # Handle network issues gracefully
          flash("⚠️ Network error: Unable to reach the moderation service. Please check your internet connection.", "error")
          result = None  # Or handle as you need
        
        # ✅ ONLY approved posts reach here
        submit_status = request.form.get("status", "draft")

        if submit_status == "published":
            post.status = "published"
            post.is_published = True
            post.published_at = datetime.utcnow()
        
        elif submit_status == "scheduled":
          scheduled_date = form.scheduled_at.data
          if not scheduled_date:
              flash("Please select a schedule date", "danger")
              return redirect(request.url)
          post.status = "scheduled"
          post.scheduled_at = scheduled_date
          post.is_published = False
        
        else:
            post.status = "draft"
            post.is_published = False
            post.content = form.content.data
        
        if not safe_commit():
          print("Post submitted successfully.")

        flash("Post submitted successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/create.html",
        form=form,
        post=post,
        rules=rules,
        moderation_status=status if post else None,
        moderation_reason=reason if post else None,
        existing_tags=[t.name for t in post.tags] if post and post.id else []
    )

@admin_bp.route("/post/draft", methods=["POST"])
@csrf.exempt
@login_required
def save_draft():
    content = request.form.get("content", "").strip()
    if not content:
        return jsonify({"status": "ignored"})

    # Save draft logic here
    post_id = request.form.get("post_id")
    if post_id:
        post = Post.query.get(post_id)
        if post and post.user_id == current_user.id:
            post.content = content
            post.status = "draft"
            if not safe_commit():
              print("Post saved as draft.")
            return jsonify({"status": "updated", "post_id": post.id})

    # If new draft
    post = Post(
        user_id=current_user.id,
        content=content,
        status="draft",
        is_published=False
    )
    db.session.add(post)
    if not safe_commit():
        print("Failed to save post")
    return jsonify({"status": "saved", "post_id": post.id})

@admin_bp.route("/post/user/<int:id>/submit", methods=["POST"])
@login_required
def submit_user_post(id):
    post = Post.query.get_or_404(id)

    # Can only submit own posts
    if post.user_id != current_user.id:
        flash("You cannot submit this post", "danger")
        return redirect(url_for("admin.dashboard"))

    # Can only submit draft or rejected post (if resubmissions < 2)
    if post.status == "published":
        flash("Post is already published", "info")
        return redirect(url_for("admin.dashboard"))

    if post.status == "rejected" and post.resubmission_count >= 2:
        flash("Maximum resubmissions reached", "danger")
        return redirect(url_for("admin.dashboard"))

    # Run auto moderation
    result = auto_moderate(post, current_user)
    status = result["status"]
    reason = result.get("reason")
    post.status = status
    post.rejection_reason = reason
    post.is_published = (status == "published")

    if not safe_commit():
        print("Failed to publish post")
    flash(f"Post submitted: {status.upper()}" + (f" ({reason})" if reason else ""), "success")
    return redirect(url_for("admin.dashboard"))

@csrf.exempt
@admin_bp.route("/upload-image", methods=["POST"])
@login_required
def upload_image_route():
    current_app.logger.info("Upload route hit")
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    url = upload_image_file(file, folder="SuperiorNews/editor")  # <-- use your helper function
    if not url:
        return jsonify({"error": "Upload failed"}), 500

    return jsonify({"location": url}), 200

@admin_bp.route("/post/<int:id>/approve", methods=["POST"])
@admin_bp.route("/approve/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
def approve_post(id):
    post = Post.query.get_or_404(id)

    post.status = "published"
    post.is_published = True
    post.rejection_reason = None

    post.author.rejected_posts = (post.author.rejected_posts or 0) + 1

    if not safe_commit():
        print("Failed to approve post")
    flash("Post approved!", "success")

    # redirect based on where request came from
    next_page = request.referrer or url_for("admin.dashboard")
    return redirect(next_page)

@admin_bp.route("/post/<int:id>/reject", methods=["POST"])
@admin_bp.route("/reject/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
def reject_post(id):
    post = Post.query.get_or_404(id)
    reason = request.form.get("reason", "No reason provided")

    post.status = "rejected"
    post.is_published = False
    post.rejection_reason = reason

    post.author.rejected_posts = (post.author.rejected_posts or 0) + 1

    if not safe_commit():
        print("Failed to reject post")
    flash("Post rejected!", "danger")

    next_page = request.referrer or url_for("admin.dashboard")
    return redirect(next_page)

@admin_bp.route("/messages")
@login_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    message = ContactMessage.query.filter_by(type="report")
    mess = ContactMessage.query.filter_by(is_replied=False)
    return render_template("admin/messages.html", mess=mess, message=message, messages=messages)

@admin_bp.route("/messages/<int:id>/reply", methods=["POST"])
@login_required
@csrf.exempt
def reply_message(id):
    msg = ContactMessage.query.get_or_404(id)

    reply_text = request.form.get("reply")

    """mail_msg = MailMessage(
        subject=f"Re: {msg.subject or 'Your message'}",
        recipients=[msg.email],
        body=reply_text
    )

    mail.send(mail_msg)"""
    
    success = send_email(
        msg.email,
        f"Re: {msg.subject or 'Your message'}",
        reply_text
    )

    if success:
      msg.is_replied = True
      if not safe_commit():
        print("Failed to send message")
  
      flash("Reply sent successfully.", "success")
    else:
      flash(
          "Reply saved, but email could not be sent. Please check your internet connection.",
          "warning"
      )

    return redirect(url_for("admin.admin_messages"))

@admin_bp.route("/messages/<int:id>")
@login_required
def view_message(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    if not safe_commit():
        print("Failed to read messages")

    return render_template("admin/message_detail.html", msg=msg)

@admin_bp.route("/analytics")
@login_required
def analytics():
    range_days = int(request.args.get("range", 7))

    # -----------------------------
    # BASIC COUNTS
    # -----------------------------
    #total_posts = Post.query.count()
    total_posts, total_posts_growth = analytics_block(
        Post, Post.created_at, range_days
    )
    #total_registered_users = User.query.count()
    total_registered_users, total_registered_users_growth = analytics_block(
        User, User.created_at, range_days
    )
    total_deleted_accounts = User.query.filter_by(is_deleted=True).count()
    total_caption_users = CaptionHistory.query.distinct(CaptionHistory.user_id).count()

    total_likes = db.session.query(
        func.sum(Post.likes)
    ).scalar() or 0
    total_replies = Comment.query.count()
    total_repost = Repost.query.count()

    # -----------------------------
    # VIEWS & ENGAGEMENT
    # -----------------------------
    total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0
    total_impressions = db.session.query(db.func.sum(Post.impressions)).scalar() or 0
    total_profile_visits = db.session.query(db.func.sum(User.profile_visits)).scalar() or 0
    total_shares = db.session.query(db.func.sum(Post.shares)).scalar() or 0

    total_engagements = total_likes + total_replies + total_shares
    total_engagement_rate = (
        round((total_engagements / total_impressions) * 100, 2)
        if total_impressions > 0 else 0
    )

    # -----------------------------
    # READ TIME
    # -----------------------------
    total_read_time = db.session.query(
        db.func.sum(Post.read_time)
    ).scalar() or 0

    total_active_users = db.session.query(
        db.func.count(db.func.distinct(Post.user_id))
    ).scalar() or 0

    # -----------------------------
    # PLATFORM CHART DATA
    # -----------------------------
    platforms = db.session.query(
        CaptionHistory.platform,
        db.func.count()
    ).group_by(CaptionHistory.platform).all()

    # -----------------------------
    # GROWTH PLACEHOLDERS (SAFE DEFAULTS)
    # -----------------------------
    growth_defaults = 0

    return render_template(
        "admin/analytics.html",
        range_days=range_days,

        # Totals
        total_views=total_views,
        total_read_time=total_read_time,
        total_active_users=total_active_users,
        total_registered_users=total_registered_users,
        total_likes=total_likes,
        total_replies=total_replies,
        total_posts=total_posts,
        total_deleted_accounts=total_deleted_accounts,
        total_caption_users=total_caption_users,

        total_repost=total_repost,
        total_impressions=total_impressions,
        total_profile_visits=total_profile_visits,
        total_shares=total_shares,
        total_engagements=total_engagements,
        total_engagement_rate=total_engagement_rate,

        # Growth (can later be dynamic)
        growth_percentage=growth_defaults,
        total_read_time_growth=growth_defaults,
        total_active_users_growth=growth_defaults,
        total_registered_users_growth=growth_defaults,
        total_likes_growth=growth_defaults,
        total_replies_growth=growth_defaults,
        total_posts_growth=growth_defaults,
        total_deleted_accounts_growth=growth_defaults,
        total_caption_users_growth=growth_defaults,
        total_repost_growth=growth_defaults,
        total_impressions_growth=growth_defaults,
        total_profile_visits_growth=growth_defaults,
        total_shares_growth=growth_defaults,
        total_engagements_growth=growth_defaults,
        total_engagement_rate_growth=growth_defaults,

        platforms=platforms
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
    if not safe_commit():
        print("Failed to delete post")

    flash("Post deleted", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("admin.login"))

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = AppSettings.query.first()

    if not settings:
        settings = AppSettings()
        db.session.add(settings)
        if not safe_commit():
          print("Failed to save settings")

    form = PrivacyTermsForm(obj=settings)

    if form.validate_on_submit():
        settings.privacy_policy = form.privacy_policy.data
        settings.terms_conditions = form.terms_conditions.data
        if not safe_commit():
          print("Failed to save privacy")
        flash("Settings updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/settings.html",
        form=form,
        settings=settings
    )

@admin_bp.route("/my-posts")
@login_required
def myposts():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all").lower()

    # Start query with all posts
    query = Post.query

    # Search by title if query provided
    if q:
        query = query.filter(Post.title.ilike(f"%{q}%"))

    # Filter by status if not "all"
    if status == "published":
        query = query.filter_by(status="published")
    elif status == "draft":
        query = query.filter_by(status="draft")
    elif status == "pending":
        query = query.filter_by(status="pending")
    elif status == "rejected":
        query = query.filter_by(status="rejected")

    # Order by newest first
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=10)

    return render_template(
        "admin/my_posts.html",
        posts=posts,
        q=q,
        status=status
    )

# Users (optional)
@admin_bp.route("/users")
@login_required
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users_list)

@admin_bp.route("/user/<int:user_id>/toggle", methods=["POST"])
@login_required
@csrf.exempt
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("You cannot block yourself!", "warning")
        return redirect(url_for("admin.users"))

    user.is_blocked = not user.is_blocked
    user.is_active = not user.is_active
    if not safe_commit():
        print("Failed to block users")
    flash(f"{user.username} has been {'blocked' if not user.is_active else 'restored'}.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
@csrf.exempt
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    if not safe_commit():
        print("Failed to delete users")
    flash(f"{user.username} has been deleted.", "success")
    return redirect(url_for("admin.users"))