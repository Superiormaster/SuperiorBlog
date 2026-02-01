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
from app.utils.admin_email import (
    send_weekly_digest_to_all,
    send_welcome_email, send_latest_news
)
from app.utils.db_helpers import safe_commit
from app.utils.email import send_email, send_bulk_email
from app.models import Post, AppSettings, CaptionHistory, User, ContactMessage, Repost, Subscriber, DigestDraft, BreakingNews, Tag, Comment
from app.extensions import db, csrf, mail
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.analytics import analytics_block
from sqlalchemy import func
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

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid username/email or password", "danger")
            return redirect(url_for("admin.login"))

        if user and user.check_password(form.password.data) and user.is_admin:
            login_user(user)
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
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))
  
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

@admin_bp.route('/admin/subscribers')
@login_required
def list_subscribers():
    subscribers = Subscriber.query.all()
    return render_template("admin/subscribers.html", subscribers=subscribers)

@admin_bp.route('/admin/draft/preview/<int:id>') 
@login_required 
@csrf.exempt
def preview_draft(id): 
  draft = DigestDraft.query.get_or_404(id) 
  return render_template('admin/draft_view.html', draft=draft)

@admin_bp.route('/admin/draft/create', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def create_draft(): 
  if request.method == 'POST': 
    subject = request.form.get('subject')
    content = request.form.get('html_content')

    draft = DigestDraft(
        subject=subject,
        html_content=content
    )
    db.session.add(draft)
    if not safe_commit():
        print("Failed to save draft")

    flash('Draft saved')
    return redirect(url_for('admin.preview_draft', id=draft.id))

  return render_template('admin/subscribers_draft.html')

@admin_bp.route('/admin/draft/digest/<int:id>', methods=['POST'])
@login_required 
@csrf.exempt
def send_draft_digest(id): 
  draft = DigestDraft.query.get_or_404(id)

  if draft.is_sent:
    flash('This digest was already sent')
    return redirect(url_for('admin.dashboard'))

  subscribers = Subscriber.query.filter_by(
    is_active=True,
    receive_digest=True
  ).all()

  for s in subscribers:
    html = draft.html_content + f"""
    <p style='font-size:12px'>
      <a href='https://yourdomain.com/unsubscribe/{s.unsubscribe_token}'>
        Unsubscribe
      </a>
    </p>
    """
    send_bulk_email(s.email, draft.subject, html)

  draft.is_sent = True
  if not safe_commit():
    print("Failed to reject post")

  flash('Digest sent successfully')
  return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/draft/send/<int:id>', methods=['POST'])
@login_required
@csrf.exempt
def send_draft(id):
    draft = DigestDraft.query.get_or_404(id)
    if draft.is_sent:
        flash("This draft was already sent")
        return redirect(url_for('admin.dashboard'))

    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()
    for s in subscribers:
        html = draft.html_content + f"""
        <p style='font-size:12px'>
        <a href='https://yourdomain.com/unsubscribe/{s.unsubscribe_token}'>Unsubscribe</a>
        </p>
        """
        send_bulk_email(s.email, draft.subject, html)

    draft.is_sent = True
    if not safe_commit():
        print("Failed to send draft")
    flash("Digest sent successfully")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/email/send-digest', methods=['POST'])
@csrf.exempt
def send_digest():
    send_weekly_digest_to_all()
    flash("Weekly digest sent successfully")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/email/welcome/<int:id>', methods=['POST'])
@csrf.exempt
def resend_welcome(id):
    subscriber = Subscriber.query.get_or_404(id)
    send_welcome_email(subscriber.email, subscriber.unsubscribe_token)
    flash("Welcome email resent")
    return redirect(url_for('admin.list_subscribers'))

@admin_bp.route('/admin/subscriber/<int:id>/toggle-digest', methods=['POST'])
@csrf.exempt
def toggle_digest(id):
    subscriber = Subscriber.query.get_or_404(id)
    subscriber.receive_digest = not subscriber.receive_digest
    if not safe_commit():
        print("Failed to reject post")

    flash("Subscriber preference updated")
    return redirect(url_for('admin.list_subscribers'))

@admin_bp.route('/admin/drafts')
@login_required
def list_drafts():
    drafts = DigestDraft.query.order_by(DigestDraft.id.desc()).all()
    return render_template('admin/drafts.html', drafts=drafts)

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
    
    unique_visitors = db.session.query(
        func.count(func.distinct(Post.user_id))
    ).scalar() or 0
    
    #total_registered_users = User.query.count()
    total_registered_users, total_registered_users_growth = analytics_block(
        User, User.created_at, range_days
    )
    total_deleted_accounts = User.query.filter_by(is_deleted=True).count()
    total_caption_users = CaptionHistory.query.distinct(CaptionHistory.user_id).count()
    
    total_avg_posts = round(
    total_posts / total_registered_users, 2
    ) if total_registered_users > 0 else 0
    
    total_avg_caption = round(
        total_caption_users / total_registered_users, 2
    ) if total_registered_users > 0 else 0
    
    total_avg_posts_growth = growth_defaults
    total_avg_caption_growth = growth_defaults

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
        total_avg_caption=total_avg_caption,
        total_avg_caption_growth=total_avg_caption_growth,
        total_avg_posts=total_avg_posts,
        total_avg_posts_growth=total_avg_posts_growth,
        unique_visitors=unique_visitors,

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