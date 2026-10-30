from collections import OrderedDict, defaultdict
from datetime import datetime, UTC, timedelta
from urllib.parse import quote, urlparse
import os
import re
import secrets
import time
import traceback
import uuid

import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    session,
    jsonify,
    current_app,
    flash,
    make_response,
    abort,
)

from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required,
)

from sqlalchemy import (
    and_,
    desc,
    distinct,
    func,
    or_,
)

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from cloudinary.exceptions import Error as CloudinaryError

from app.models import (
    Post,
    Comment,
    Like,
    Subscriber,
    ContactMessage,
    Reply,
    Category,
    User,
    AppSettings,
    Tag,
    post_tags,
    Label,
    ProfileVisit,
    FootballCache,
    PageView,
    Ad,
)

from app.services.superior_ads import (
    get_superior_ad,
    make_ad_tracking_context,
)

from app.moderation.engine import auto_moderate
from app.moderation.rules import CATEGORY_RULES
from app.moderation.spam import is_spam
from app.moderation.grammar import grammar_score
from app.moderation.duplicate import hash_content

from app.utils.helper import process_tags, get_related_posts
from app.utils.cloudinary_helper import upload_image_file
from app.utils.adInjector import inject_inpost_content
from app.utils.email import send_email
from app.utils.admin_email import send_welcome_email
from app.utils.decorators import generate_unique_slug
from app.utils.db_helpers import safe_commit

from app.extensions import db, cache, csrf

from app.forms import (
    UserLoginForm,
    UserRegisterForm,
    ChangePasswordForm,
    PostForm,
    ProfileForm,
    DeletePostForm,
    SubmitPostForm,
    ResetPasswordForm,
    ForgotPasswordForm,
    SubscribeForm,
)

public_bp = Blueprint(
    "public",
    __name__,
    template_folder="../templates/user",
)

# --------------------------------------------------
# PUBLIC CACHE HELPERS
# --------------------------------------------------

PUBLIC_CACHE_TIMEOUT = 60
HOMEPAGE_CACHE_TIMEOUT = 60
CATEGORY_CACHE_TIMEOUT = 120
TAG_CACHE_TIMEOUT = 120


def clear_public_content_cache(category_id=None):
    keys = (
        "public_homepage_categories",
        "public_popular_tags",
        "public_homepage_data",
        "public_breaking_posts",
        "public_latest_posts",
        "public_popular_posts",
    )

    for key in keys:
        try:
            cache.delete(key)
        except Exception:
            current_app.logger.exception(
                "Failed to invalidate public cache: %s",
                key,
            )

    if category_id is not None:
        try:
            cache.delete(
                f"public_category_trending_ids_{category_id}"
            )
        except Exception:
            current_app.logger.exception(
                "Failed to invalidate trending cache for category %s",
                category_id,
            )


def get_cached_value(key, timeout, loader):
    """
    Return cached data when available.

    If the cache is unavailable, load fresh data instead.
    """
    try:
        value = cache.get(key)

        if value is not None:
            return value
    except Exception:
        current_app.logger.exception(
            "Cache read failed for key: %s",
            key,
        )

    value = loader()

    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        current_app.logger.exception(
            "Cache write failed for key: %s",
            key,
        )

    return value

def validate_tribe_url(url):
    if not url:
        return True

    parsed = urlparse(url)

    return (
        parsed.scheme == "https"
        and parsed.netloc
    )
  
def track_login(user):
    user.login_count = (user.login_count or 0) + 1
    user.last_login = datetime.now(UTC)
    safe_commit()

@public_bp.route("/test_session")
def test_session():
    session['test'] = 'ok'
    return f"Session test: {session.get('test')}"

@public_bp.route('/register', methods=['GET', 'POST'])
def user_register():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    form = UserRegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter(
            (User.username == form.username.data) |
            (User.email == form.email.data)
        ).first()
        if existing_user:
            flash("Username or email already exists. Please choose another.", "danger")
            return redirect(url_for('public.user_register'))

        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        existing_subscriber = Subscriber.query.filter_by(email=user.email).first()
        if not existing_subscriber:
          subscriber = Subscriber(email=user.email, user_id=user.id, is_active=True)
          db.session.add(subscriber)
        elif not existing_subscriber.is_active:
            existing_subscriber.is_active = True
            db.session.add(existing_subscriber)

        if not safe_commit():
          print("Failed to register user")
          flash("Error creating account. Try again.", "danger")
          return redirect(url_for('public.user_register'))

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('public.user_login'))
    return render_template('user/register.html', form=form)

@public_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if current_user.is_authenticated:
        next_page = request.args.get('next') or url_for('public.user_dashboard')
        return redirect(next_page)

    form = UserLoginForm()
    next_page = request.args.get('next', url_for('public.user_dashboard'))

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # User exists and password is correct
        if user and user.check_password(form.password.data) and not user.is_admin:
            login_user(user, remember=form.remember_me.data)
            track_login(user)

            # AJAX modal login
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # If user is completely new (first-time login) in modal, tell them to sign up
                if not user.profile_completed:  # assuming you have a boolean column profile_completed
                    return jsonify({
                        "success": False,
                        "message": "Please sign up first to complete your profile."
                    })
                return jsonify({"success": True})

            # Normal page login
            flash("Logged in successfully!", "success")
            if not user.profile_completed:
                # Redirect first-time login users to profile setup
                return redirect(url_for('public.profile_setup'))
            return redirect(next_page)

        # Invalid login
        else:
            msg = "No account found. Please sign up." if not user else "Incorrect password. Please check your password"
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": msg})
            flash(msg, "error")
            return redirect(url_for('public.user_login', next=next_page))

    # Form validation failed
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": False, "message": "Form validation failed."})

    # GET request → show login page
    return render_template('user/login.html', form=form, GOOGLE_CLIENT_ID=current_app.config["GOOGLE_CLIENT_ID"]
    )

@public_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not form.email.data:
          flash("Please enter your email", "error")

        if user:
            # Generate a token (you can use itsdangerous)
            token = user.generate_reset_token()
            reset_url = url_for("public.reset_password", token=token, _external=True)
            success = send_email(user.email, "Reset Your Password", f"Click here to reset: {reset_url}")
            if success:
              flash("Check your email for reset instructions.", "info")
            else:
              flash(
                  "Reset link saved, but email could not be sent. Please check your internet connection.",
                  "warning"
              )
        else:
            flash("If that email is registered, you will receive a reset link.", "info")
        return redirect(url_for("public.user_login"))
    return render_template("user/forgot_password.html", form=form)

@public_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token = token or request.form.get("token")
  
    user = User.verify_reset_token(token)
    if not user:
        flash("Invalid or expired token", "danger")
        return redirect(url_for("public.user_login"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        if not safe_commit():
          print("Failed to reset password")
        flash("Your password has been reset. Please log in", "success")
        return redirect(url_for("public.user_login"))

    return render_template("user/reset_password.html", token=token, form=form)

@public_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def user_change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            if not safe_commit():
              print("Failed to change password")
            flash("Password updated successfully!", "success")
            return redirect(url_for('public.user_dashboard'))
    return render_template('user/change_password.html', form=form)

@public_bp.route("/profile/setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    next_page = request.args.get('next', url_for('public.user_dashboard'))

    if current_user.profile_completed:
        return redirect(next_page)

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        current_user.profile_completed = True
        if not safe_commit():
          print("Failed to setup profile")

        flash("Profile completed successfully", "success")
        next_page = request.args.get('next', url_for('caption.caption_page'))

        return redirect(next_page)

    return render_template(
        "user/profile_setup.html",
        form=form,
        user=current_user
    )

@public_bp.route("/profile/<username>")
@login_required
@csrf.exempt
def user_profile(username):
    user = User.query.filter_by(
        username=username
    ).first_or_404()

    is_owner = current_user.id == user.id

    # Do not count the owner's visits to their own profile.
    if not is_owner:
        try:
            visit = ProfileVisit(
                visited_user_id=user.id,
                visitor_id=current_user.id,
            )

            db.session.add(visit)

            if not safe_commit():
                current_app.logger.error(
                    "Failed to record profile visit for user %s",
                    user.id,
                )

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Error recording profile visit"
            )

    return render_template(
        "user/profile.html",
        user=user,
        is_owner=is_owner,
    )

@public_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        if form.username.data != current_user.username:
            exists = User.query.filter_by(username=form.username.data).first()
            if exists:
                flash("Username already taken.", "error")
                return redirect(url_for("public.edit_profile"))

        form.populate_obj(current_user)
        if not safe_commit():
          print("Failed to edit profile")

        flash("Profile updated successfully.", "success")
        return redirect(
            url_for("public.user_profile", username=current_user.username)
        )

    return render_template(
        "user/edit_profile.html",
        form=form
    )

def calculate_growth(current, previous):
    if previous == 0 and current > 0:
        return 100
    if previous > 0:
        return round(((current - previous) / previous) * 100, 2)
    return 0

@public_bp.route("/analysis/", defaults={"page_path": None})
@public_bp.route('/analysis/<path:page_path>')
@login_required
def user_analysis(page_path):
    try:
      range_days = int(request.args.get("range", "30"))
    except (TypeError, ValueError):
       range_days = 7
    now = datetime.utcnow()

    if range_days not in [7, 30]:
        range_days = 30
    
    start_date = now - timedelta(days=range_days)

        # Only retrieve posts created during the selected period.
    posts = (
        Post.query
        .filter(
            Post.user_id == current_user.id,
            Post.created_at >= start_date,
        )
        .order_by(Post.created_at.desc())
        .all()
    )

    post_ids = [post.id for post in posts]
    no_of_posts = len(posts)

    total_views = sum(post.views or 0 for post in posts)
    total_read_time = sum(post.read_time or 0 for post in posts)
    total_shares = sum(post.shares or 0 for post in posts)

    # Aggregate likes in one database query.
    likes_map = {}

    if post_ids:
        likes_map = dict(
            db.session.query(
                Like.post_id,
                func.count(Like.id),
            )
            .filter(Like.post_id.in_(post_ids))
            .group_by(Like.post_id)
            .all()
        )

    total_likes = sum(likes_map.values())

    # Count replies through SQL rather than loading every reply.
    total_replies = 0

    if post_ids:
        total_replies = (
            db.session.query(func.count(Reply.id))
            .join(Comment, Reply.comment_id == Comment.id)
            .filter(Comment.post_id.in_(post_ids))
            .scalar()
        ) or 0

    profile_visits = (
        ProfileVisit.query
        .filter_by(visited_user_id=current_user.id)
        .count()
    )

    # ✅ Average time per view
    pageview_query = db.session.query(
        func.coalesce(func.sum(PageView.read_time), 0)
    )
    
    if page_path:
        pageview_query = pageview_query.filter(PageView.path == page_path)

    total_time_minutes = pageview_query.filter(
        PageView.created_at >= datetime.utcnow() - timedelta(days=range_days)
    ).scalar()

    # Previous period
    previous_views = previous_likes = previous_read_time =  previous_posts_count = 0
    engagement_rate = 0
    previous_shares = 0
    previous_avg_read_time = previous_engagement_rate = 0
    engagement_rate_growth = 0
    previous_profile_visits = previous_total_replies = previous_total_shares = 0

    period_length = now - start_date
    prev_start = start_date - period_length

    previous_posts_query = Post.query.filter(
        Post.user_id == current_user.id,
        Post.created_at >= prev_start,
        Post.created_at < start_date,
    )

    previous_posts = previous_posts_query.all()
    previous_post_ids = [post.id for post in previous_posts]

    previous_posts_count = len(previous_posts)

    previous_views = sum(
        post.views or 0
        for post in previous_posts
    )

    previous_read_time = sum(
        post.read_time or 0
        for post in previous_posts
    )

    previous_total_shares = sum(
        post.shares or 0
        for post in previous_posts
    )

    previous_likes = 0
    previous_total_replies = 0

    if previous_post_ids:
        previous_likes = (
            db.session.query(func.count(Like.id))
            .filter(Like.post_id.in_(previous_post_ids))
            .scalar()
        ) or 0

        previous_total_replies = (
            db.session.query(func.count(Reply.id))
            .join(Comment, Reply.comment_id == Comment.id)
            .filter(Comment.post_id.in_(previous_post_ids))
            .scalar()
        ) or 0

    previous_profile_visits = (
        ProfileVisit.query
        .filter(
            ProfileVisit.visited_user_id == current_user.id,
            ProfileVisit.created_at >= prev_start,
            ProfileVisit.created_at < start_date,
        )
        .count()
    )

    previous_total_engagements = (
        previous_likes
        + previous_total_replies
        + previous_total_shares
    )

    previous_engagement_rate = (
        round(
            previous_total_engagements / previous_views * 100,
            2,
        )
        if previous_views
        else 0
    )

    previous_avg_read_time = (
        round(previous_read_time / previous_posts_count, 2)
        if previous_posts_count
        else 0
    )

    views_growth = calculate_growth(total_views, previous_views)
    likes_growth = calculate_growth(total_likes, previous_likes)
    read_time_growth = calculate_growth(total_read_time, previous_read_time)
    profile_growth = calculate_growth(profile_visits, previous_profile_visits)
    replies_growth = calculate_growth(total_replies, previous_total_replies)
    shares_growth = calculate_growth(total_shares, previous_total_shares)
    engagement_rate_growth = calculate_growth(
          engagement_rate,
          previous_engagement_rate
      )
    avg_read_time = round(total_read_time / no_of_posts, 2) if no_of_posts else 0
    avg_read_time_growth = calculate_growth(avg_read_time, previous_avg_read_time)
    avg_time_per_view = round(
        total_time_minutes / total_views, 2
    ) if total_views else 0
    posts_growth = calculate_growth(no_of_posts, previous_posts_count)
    total_engagements = total_likes  + total_replies + total_shares
    growth_percentage = calculate_growth(total_engagements, previous_total_engagements)

    engagements_growth = calculate_growth(
        total_engagements, previous_total_engagements
    )

    # Posts per day
    if posts:
        first_date = min(p.created_at for p in posts if p.created_at)
        days_active = max((now - first_date).days, 1)
        posts_per_day = round(no_of_posts / days_active, 2)
    else:
        posts_per_day = 0

    avg_read_time = round(total_read_time / no_of_posts, 2) if no_of_posts else 0
    engagement_rate = round((total_engagements / total_views) * 100, 2) if total_views else 0

    likes_map = dict(
        db.session.query(Like.post_id, func.count(Like.id))
        .group_by(Like.post_id)
        .all()
    )

    best_post = max(
        posts,
        key=lambda p: ((p.views or 0), likes_map.get(p.id, 0)),
        default=None
    )

    # Chart data (sorted)
    daily_views = defaultdict(int)
    daily_likes = defaultdict(int)

    for post in posts:
        if not post.created_at:
            continue

        day = post.created_at.strftime("%Y-%m-%d")

        daily_views[day] += post.views or 0
        daily_likes[day] += likes_map.get(post.id, 0)

    chart_labels = sorted(daily_views.keys())

    views_data = [
        daily_views[day]
        for day in chart_labels
    ]

    likes_data = [
        daily_likes[day]
        for day in chart_labels
    ]

    return render_template(
        "user/analysis.html",
        total_views=total_views,
        total_likes=total_likes,
        total_read_time=total_read_time,
        total_time_minutes=total_time_minutes,
        no_of_posts=no_of_posts,
        posts_per_day=posts_per_day,
        best_post=best_post,
        likes_map=likes_map,
        growth_percentage=growth_percentage,
        chart_labels=chart_labels,
        views_data=views_data,
        likes_data=likes_data,
        profile_visits=profile_visits,
        total_replies=total_replies,
        total_engagements=total_engagements,
        impressions=total_views,
        total_shares=total_shares,

        profile_growth=profile_growth,
        replies_growth=replies_growth,
        views_growth=views_growth,
        likes_growth=likes_growth,
        read_time_growth=read_time_growth,
        posts_growth=posts_growth,
        engagement_rate=engagement_rate,
        engagement_rate_growth=engagement_rate_growth,
        avg_read_time_growth=avg_read_time_growth,
        avg_time_per_view=avg_time_per_view,
        
        engagements_growth=engagements_growth,
        impressions_growth=views_growth,
        shares_growth=shares_growth
    )

@public_bp.route("/post/<int:post_id>/share", methods=["POST"])
@login_required
@csrf.exempt
def share_post(post_id):
    post_exists = db.session.query(
        Post.id
    ).filter(
        Post.id == post_id
    ).first()

    if not post_exists:
        return jsonify({
            "success": False,
            "message": "Post not found.",
        }), 404

    try:
        db.session.query(Post).filter(
            Post.id == post_id
        ).update(
            {
                Post.shares: func.coalesce(Post.shares, 0) + 1,
            },
            synchronize_session=False,
        )

        if not safe_commit():
            return jsonify({
                "success": False,
                "message": "Unable to record share.",
            }), 500

        return jsonify({
            "success": True,
        })

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to increment shares for post %s",
            post_id,
        )

        return jsonify({
            "success": False,
            "message": "Unable to record share.",
        }), 500

@public_bp.route('/dashboard')
@login_required
def user_dashboard():
    delete_form = DeletePostForm()
    submit_form = SubmitPostForm()

    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "")
    status = request.args.get("status", "all")
    per_page=15

    query = Post.query.filter_by(user_id=current_user.id)

    if q:
        query = query.filter(Post.title.ilike(f"%{q}%"))

    if status == "draft":
        query = query.filter(Post.status == "draft")
    elif status == "rejected":
        query = query.filter(Post.status == "rejected")
    elif status == "published":
        query = query.filter(Post.status == "published")

    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "user/dashboard.html",
        posts=posts,
        q=q,
        status=status,
        delete_form=delete_form,
        submit_form=submit_form
    )

@public_bp.route("/post/create", methods=["GET", "POST"], endpoint='create_post')
@login_required
def user_create():
    return user_create_or_edit()
@public_bp.route("/post/<int:id>/edit", methods=["GET", "POST"], endpoint='edit_post')
@login_required
def user_edit(id):
    return user_create_or_edit(id)

def user_create_or_edit(id=None):
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
        return redirect(url_for("public.user_dashboard"))

    # 🔐 Ownership check for editing
    if post and post.id and post.user_id != current_user.id:
        flash("You are not allowed to edit this post.", "danger")
        return redirect(url_for("public.user_dashboard"))

    # Block editing if published
    if post and post.status == "published":
        flash("Published posts cannot be edited.", "warning")
        return redirect(url_for("public.user_dashboard"))


    # Block if rejected but max resubmissions reached
    if post and post.status == "rejected" and (post.resubmission_count or 0) >= 2:
        flash("Maximum resubmissions reached.", "danger")
        return redirect(url_for("public.user_dashboard"))

    # Set choices for category and labels
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    form.labels.choices = [(l.id, l.name) for l in Label.query.all()]

    # Pre-fill form on GET
    if request.method == "GET" and post:
      form.category.data = post.category_id
      form.labels.data = [l.id for l in post.labels]
    
      form.tribe_url.data = post.tribe_url or ""
      form.tribe_title.data = post.tribe_title or ""
      form.tribe_description.data = post.tribe_description or ""
      form.tribe_button_text.data = post.tribe_button_text or ""

    guidelines = rules

    if form.validate_on_submit():
        is_new = False
  
        featured_image = request.form.get("featured_image")
        content_html = request.form.get("content", "")
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator=" ").strip()
        if not text:
            flash("Post content cannot be empty.", "danger")
            return render_template("user/create.html", form=form, rules=rules, post=post)

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
                content_hash=hash_content(content_html),
                resubmission_count=0,
                status="draft",
                is_published=False,
                tribe_url=form.tribe_url.data.strip() if form.tribe_url.data else None,
                tribe_title=form.tribe_title.data.strip() if form.tribe_title.data else None,
                tribe_description=form.tribe_description.data.strip() if form.tribe_description.data else None,
                tribe_button_text=form.tribe_button_text.data.strip() if form.tribe_button_text.data else None,
            )
            db.session.add(post)
        else:
            # Editing existing post
            post.title = form.title.data
            post.content = content_html.strip()
            post.featured_image = request.form.get("featured_image")
            post.content_hash = hash_content(content_html)
            post.tribe_url = (
                form.tribe_url.data.strip()
                if form.tribe_url.data
                else None
            )
            
            post.tribe_title = (
                form.tribe_title.data.strip()
                if form.tribe_title.data
                else None
            )
            
            post.tribe_description = (
                form.tribe_description.data.strip()
                if form.tribe_description.data
                else None
            )
            
            post.tribe_button_text = (
                form.tribe_button_text.data.strip()
                if form.tribe_button_text.data
                else None
            )
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
        form.labels.choices = [(label.id, label.name) for label in Label.query.all()]
        post.labels = Label.query.filter(Label.id.in_(form.labels.data)).all()

        # Assign tags
        raw_tags = request.form.get("tags", "")
        post.tags = process_tags(raw_tags)
        print("Draft content size (bytes):", len(request.form.get("content", "").encode("utf-8")))

        if not safe_commit():
            flash(
                "Unable to save the draft. Please try again.",
                "danger",
            )
            return redirect(url_for("public.user_dashboard"))
        
        clear_public_content_cache()
        
        flash("Draft saved successfully.", "success")
        return redirect(url_for("public.user_dashboard"))

    return render_template("user/create.html", form=form, post=post, rules=rules)

@public_bp.route("/post/draft", methods=["POST"])
@csrf.exempt
@login_required
def save_draft():
    """
    Save or update a draft.

    Handles:
    - title
    - content
    - featured image
    - category
    - labels
    - tags
    - Tribe conversation fields
    """

    content_html = request.form.get("content", "").strip()

    title = (
        request.form.get("title", "").strip()
        or "Untitled Draft"
    )

    featured_image = (
        request.form.get("featured_image", "").strip()
        or None
    )

    category_id = request.form.get("category")

    label_ids = request.form.getlist("labels")

    raw_tags = request.form.get("tags", "")

    post_id = request.form.get("post_id")

    tribe_url = (
        request.form.get("tribe_url", "").strip()
        or None
    )

    tribe_title = (
        request.form.get("tribe_title", "").strip()
        or None
    )

    tribe_description = (
        request.form.get("tribe_description", "").strip()
        or None
    )

    tribe_button_text = (
        request.form.get("tribe_button_text", "").strip()
        or None
    )

    if not content_html:
        return jsonify({
            "status": "ignored"
        })

    if post_id:

        post = Post.query.get(post_id)

        if not post:
            return jsonify({
                "status": "not_found"
            }), 404

        if post.user_id != current_user.id:
            return jsonify({
                "status": "forbidden"
            }), 403

        is_new = False

        if not post.slug:
            post.slug = (
                generate_unique_slug(title)
                or f"draft-{int(time.time())}"
            )

    else:

        slug = (
            generate_unique_slug(title)
            or f"draft-{int(time.time())}"
        )

        post = Post(
            user_id=current_user.id,
            title=title,
            slug=slug,
            status="draft",
            is_published=False,
            content=content_html,
            featured_image=featured_image,
            content_hash=hash_content(content_html),
        )

        # Safe to add now because slug already exists.
        db.session.add(post)

        is_new = True

    post.title = title
    post.content = content_html
    post.featured_image = featured_image

    post.status = "draft"
    post.is_published = False

    post.content_hash = hash_content(content_html)

    post.tribe_url = tribe_url
    post.tribe_title = tribe_title
    post.tribe_description = tribe_description
    post.tribe_button_text = tribe_button_text

    if not post.featured_image and content_html:

        soup = BeautifulSoup(
            content_html,
            "html.parser"
        )

        first_img = soup.find("img")

        if first_img:
            post.featured_image = first_img.get("src")

    try:

        with db.session.no_autoflush:

            if category_id:

                category = Category.query.get(
                    category_id
                )

                if category:
                    post.category = category

            try:

                label_ids = [
                    int(label_id)
                    for label_id in label_ids
                    if str(label_id).isdigit()
                ]

            except (ValueError, TypeError):

                label_ids = []

            post.labels = (
                Label.query
                .filter(
                    Label.id.in_(label_ids)
                )
                .all()
                if label_ids
                else []
            )

        post.tags = process_tags(raw_tags)

        if not safe_commit():
            db.session.rollback()
        
            current_app.logger.error(
                "Draft save transaction failed for user %s",
                current_user.id,
            )
        
            return jsonify({
                "status": "error",
                "message": "Failed to save draft.",
            }), 500
        
        clear_public_content_cache()

    except Exception as e:

        db.session.rollback()

        print(
            "========== DRAFT SAVE ERROR =========="
        )

        print(
            "Error:",
            str(e)
        )

        return jsonify({
            "status": "error",
            "message": "Failed to save draft."
        }), 500

    print(
        "========== DRAFT SAVED =========="
    )

    print(
        "Post ID:",
        post.id
    )

    print(
        "Category:",
        post.category_id
    )

    print(
        "Labels:",
        [label.id for label in post.labels]
    )

    print(
        "Tribe URL:",
        post.tribe_url
    )

    print(
        "Tribe Title:",
        post.tribe_title
    )

    print(
        "Tribe Description:",
        post.tribe_description
    )

    print(
        "Tribe Button:",
        post.tribe_button_text
    )

    print(
        "Slug:",
        post.slug
    )

    return jsonify({
        "status": "saved",
        "post_id": post.id
    })

@public_bp.route("/post/user/<int:id>/submit", methods=["POST"])
@login_required
def submit_user_post(id):
    post = Post.query.get_or_404(id)

    # Ownership check
    if post.user_id != current_user.id:
        flash("You cannot submit this post.", "danger")
        return redirect(url_for("public.user_dashboard"))

    # Only draft or rejected can be submitted
    if post.status not in ["draft", "rejected"]:
        flash("This post cannot be submitted.", "warning")
        return redirect(url_for("public.user_dashboard"))

    # Resubmission limit
    if post.status == "rejected" and (post.resubmission_count or 0) >= 2:
        flash("Maximum resubmissions reached.", "danger")
        return redirect(url_for("public.user_dashboard"))

    # Content validation
    soup = BeautifulSoup(post.content, "html.parser")
    text = soup.get_text(" ")
    word_count = len(text.split())

    if not post.content or word_count < 150:
        flash("Post content must be at least 150 words.", "danger")
        return redirect(url_for("public.user_dashboard"))

    try:
        was_rejected = post.status == "rejected"

        result = auto_moderate(post, current_user)

        status = result.get("status", "pending_review")
        reason = result.get("reason")

        post.status = status
        post.rejection_reason = reason
        post.is_published = False

        # Increment resubmission count if previously rejected
        if was_rejected and status == "rejected":
            post.resubmission_count = (post.resubmission_count or 0) + 1

        # FEATURED IMAGE (ALWAYS)
        if not post.featured_image and post.content:
          soup = BeautifulSoup(post.content, "html.parser")
          first_img = soup.find("img")
          if first_img:
            post.featured_image = first_img.get("src")

        safe_commit()

        # Flash messages
        if status == "rejected":
            flash(f"Post rejected: {reason}", "danger")

        elif status == "pending_review":
            flash("Post submitted for editorial review.", "warning")

        elif status == "approved":
            flash("Post approved and awaiting publication.", "success")

        else:
            flash(f"Moderation result: {status}", "info")

    except ConnectionError:
        db.session.rollback()
        post.status = "draft"
        post.is_published = False
        safe_commit()

        flash(
            "Moderation service unavailable. Post saved as draft.",
            "danger"
        )

    except Exception as e:
        db.session.rollback()
        print("Moderation Exception:", str(e))
        flash("Moderation error. Try again.", "danger")

    return redirect(url_for("public.user_dashboard"))

@public_bp.route("/post/<int:id>/schedule", methods=["POST"])
@login_required
def schedule_post(id):
    post = Post.query.get_or_404(id)

    if post.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("public.user_dashboard"))

    if post.status != "approved":
        flash("Only approved posts can be scheduled.", "warning")
        return redirect(url_for("public.user_dashboard"))

    scheduled_date = request.form.get("scheduled_at")

    if not scheduled_date:
        flash("Please select a valid date.", "danger")
        return redirect(url_for("public.user_dashboard"))

    try:
        parsed_date = datetime.fromisoformat(scheduled_date)
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("public.user_dashboard"))

    if parsed_date <= datetime.utcnow():
        flash("Scheduled date must be in the future.", "danger")
        return redirect(url_for("public.user_dashboard"))

    post.status = "scheduled"
    post.scheduled_at = parsed_date
    post.is_published = False

    safe_commit()

    flash("Post scheduled successfully.", "success")
    return redirect(url_for("public.user_dashboard"))

@csrf.exempt
@public_bp.route("/upload-image", methods=["POST"])
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

@public_bp.route("/post/<int:id>/delete", methods=["POST"])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    # Ownership check
    if post.user_id != current_user.id:
        flash("You are not allowed to delete this post.", "danger")
        return redirect(url_for("public.user_dashboard"))

    form = DeletePostForm()

    if form.validate_on_submit():
        db.session.delete(post)

        if not safe_commit():
            flash(
                "Failed to delete the post.",
                "danger",
            )
        else:
            clear_public_content_cache()
            flash(
                "Post deleted successfully.",
                "success",
            )

@public_bp.route("/login/google")
def google_login():
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    redirect_uri = current_app.config["REDIRECT_URI"]
    next_page = request.args.get("next", url_for("public.user_dashboard"))

    # Google OAuth URL
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={quote(next_page)}"
        "&scope=openid%20email%20profile"
        "&prompt=select_account"
        "&include_granted_scopes=true" 
    )
    return redirect(google_auth_url)

@public_bp.route("/login/google/callback")
def google_callback():
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    redirect_uri = current_app.config["REDIRECT_URI"]
    client_secret = current_app.config["CLIENT_SECRET"]
    code = request.args.get("code")
    if not code:
        flash("Google login failed: no code", "error")
        return redirect(url_for("public.user_login"))

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    try:
        response = requests.post(
            token_url,
            data=data,
            timeout=15,
        )
        response.raise_for_status()
        token_response = response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.exception(
            "Google OAuth token exchange failed"
        )
        flash(
            "Google could not log you in. Please try again.",
            "error",
        )
        return redirect(url_for("public.user_login"))

    # 🚨 Ensure id_token exists
    id_token_value = token_response.get("id_token")
    if not id_token_value:
        flash("Google could not log you in. Try again", "error")
        return redirect(url_for("public.user_login"))

    # ✅ Verify token
    idinfo = id_token.verify_oauth2_token(
        id_token_value,
        google_requests.Request(),
        client_id,
        clock_skew_in_seconds=5
    )

    # idinfo contains user info
    user_email = idinfo["email"]
    user_name = idinfo["name"]
    oauth_id = idinfo["sub"]

    # Save or get user from DB
    user = User.query.filter((User.email==user_email) | (User.oauth_id == oauth_id)).first()
    if user:
        # Update login info only
        user.last_login = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
    else:
        user = User(email=user_email, username=f"user_{uuid.uuid4().hex[:8]}", oauth_provider="google", oauth_id=oauth_id, is_active=1, created_at=datetime.utcnow(), last_login=datetime.utcnow(), login_count=1,)
        db.session.add(user)
        db.session.flush()

        existing_subscriber = Subscriber.query.filter_by(email=user.email).first()
        if not existing_subscriber:
          subscriber = Subscriber(email=user.email, user_id=user.id, is_active=True)
          db.session.add(subscriber)
        elif not existing_subscriber.is_active:
            existing_subscriber.is_active = True
            db.session.add(existing_subscriber)
        if not safe_commit():
          print("Failed to login user")

    next_page = request.args.get('state', url_for("public.user_dashboard"))

    login_user(user)
    track_login(user)
    flash("Logged in successfully", "success")

    if user.profile_completed:
        return redirect(next_page)
    return redirect(url_for("public.profile_setup"))

@public_bp.route("/auth/google/onetap", methods=["POST"])
def google_one_tap():
    data = request.get_json(silent=True) or {}
    token = data.get("credential")

    if not token:
        return jsonify({
            "success": False,
            "error": "No token provided",
        }), 400

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")

    if not client_id:
        current_app.logger.error(
            "GOOGLE_CLIENT_ID is missing from application configuration"
        )
        return jsonify({
            "success": False,
            "error": "Google login is not configured.",
        }), 500

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid Google credential.",
        }), 400
    except Exception:
        current_app.logger.exception(
            "Google One Tap verification failed"
        )
        return jsonify({
            "success": False,
            "error": "Google authentication failed.",
        }), 400

    email = (idinfo.get("email") or "").strip().lower()
    oauth_id = idinfo.get("sub")
    name = (idinfo.get("name") or "").strip()
    picture = idinfo.get("picture")

    # Do not accept an unverified Google email.
    if not email or not oauth_id or not idinfo.get("email_verified"):
        return jsonify({
            "success": False,
            "error": "A verified Google email is required.",
        }), 400

    try:
        user = User.query.filter(
            or_(
                User.oauth_id == oauth_id,
                User.email == email,
            )
        ).first()

        if user:
            # Do not silently link a different Google identity
            # to an existing account with the same email.
            if user.oauth_id and user.oauth_id != oauth_id:
                return jsonify({
                    "success": False,
                    "error": (
                        "This email is already associated with "
                        "another login method."
                    ),
                }), 409

            if not user.oauth_id:
                user.oauth_id = oauth_id
                user.oauth_provider = "google"

            if picture and not user.avatar:
                user.avatar = picture

        else:
            base_username = re.sub(
                r"[^a-zA-Z0-9_]",
                "",
                name.replace(" ", "_"),
            ).strip("_").lower()

            base_username = base_username[:20] or "user"

            username = f"{base_username}_{uuid.uuid4().hex[:8]}"

            user = User(
                email=email,
                username=username,
                oauth_provider="google",
                oauth_id=oauth_id,
                avatar=picture,
            )

            db.session.add(user)

        user.last_login = datetime.now(UTC)
        user.login_count = (user.login_count or 0) + 1

        if not safe_commit():
            return jsonify({
                "success": False,
                "error": "Unable to complete Google login.",
            }), 500

        login_user(user)

        return jsonify({
            "success": True,
            "profile_completed": bool(user.profile_completed),
            "redirect_url": (
                url_for("public.user_dashboard")
                if user.profile_completed
                else url_for("public.profile_setup")
            ),
        })

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Google One Tap account processing failed"
        )

        return jsonify({
            "success": False,
            "error": "Unable to complete Google login.",
        }), 500

@public_bp.route('/logout')
def user_logout():
    logout_user()
    flash("You are logged out", "success")
    return redirect(url_for('public.index'))

@public_bp.route("/")
def index():
    form = SubscribeForm()

    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)
    fourteen_days_ago = now - timedelta(days=14)
    six_hours_ago = now - timedelta(hours=6)

    # --------------------------------------------------
    # 1. LATEST POSTS
    # --------------------------------------------------
    latest_posts = (
        Post.query
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
            Post.created_at >= one_day_ago,
        )
        .order_by(Post.created_at.desc())
        .limit(3)
        .all()
    )

    latest_ids = [post.id for post in latest_posts]

    # --------------------------------------------------
    # 2. POPULAR POSTS
    # Aggregate comments only for eligible recent posts.
    # --------------------------------------------------
    eligible_posts = (
        db.session.query(Post.id)
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
            Post.created_at >= one_day_ago,
        )
        .subquery()
    )

    comment_counts = (
        db.session.query(
            Comment.post_id.label("post_id"),
            func.count(Comment.id).label("comment_count"),
        )
        .join(
            eligible_posts,
            eligible_posts.c.id == Comment.post_id,
        )
        .group_by(Comment.post_id)
        .subquery()
    )

    popularity_score = (
        func.coalesce(Post.views, 0)
        + func.coalesce(Post.like_count, 0)
        + func.coalesce(comment_counts.c.comment_count, 0)
    )

    popular_query = (
        db.session.query(Post)
        .outerjoin(
            comment_counts,
            Post.id == comment_counts.c.post_id,
        )
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
            Post.created_at >= one_day_ago,
        )
    )

    if latest_ids:
        popular_query = popular_query.filter(
            ~Post.id.in_(latest_ids)
        )

    popular_posts = (
        popular_query
        .order_by(
            popularity_score.desc(),
            Post.created_at.desc(),
        )
        .limit(3)
        .all()
    )

    popular_ids = [post.id for post in popular_posts]

    # --------------------------------------------------
    # 3. OTHER RECENT POSTS
    # --------------------------------------------------
    posts_query = Post.query.filter(
        Post.is_published.is_(True),
        Post.status == "published",
        Post.created_at >= fourteen_days_ago,
    )

    excluded_ids = latest_ids + popular_ids

    if excluded_ids:
        posts_query = posts_query.filter(
            ~Post.id.in_(excluded_ids)
        )

    posts = (
        posts_query
        .order_by(Post.created_at.desc())
        .limit(50)
        .all()
    )

    # --------------------------------------------------
    # 4. CATEGORY SECTIONS
    # Fetch recent posts once instead of querying every
    # category separately.
    # --------------------------------------------------
    def load_homepage_categories():
        categories = (
            Category.query
            .order_by(Category.name)
            .all()
        )

        recent_category_posts = (
            Post.query
            .filter(
                Post.is_published.is_(True),
                Post.status == "published",
                Post.created_at >= one_day_ago,
                Post.category_id.isnot(None),
            )
            .order_by(
                Post.category_id,
                Post.created_at.desc(),
            )
            .all()
        )

        grouped = defaultdict(list)

        for post in recent_category_posts:
            category_id = post.category_id

            if len(grouped[category_id]) < 3:
                grouped[category_id].append(post)

        result = OrderedDict()

        for category in categories:
            category_posts = grouped.get(category.id, [])

            if category_posts:
                result[category] = category_posts

        return result

    today_categories = get_cached_value(
        "public_homepage_categories",
        timeout=60,
        loader=load_homepage_categories,
    )

    # --------------------------------------------------
    # 5. BREAKING NEWS
    # --------------------------------------------------
    breaking_posts = (
        Post.query
        .join(Post.labels)
        .filter(
            Label.name.ilike("%breaking%"),
            Post.is_published.is_(True),
            Post.status == "published",
            Post.published_at >= six_hours_ago,
        )
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )

    # --------------------------------------------------
    # 6. POPULAR TAGS
    # --------------------------------------------------
    def load_popular_tags():
        return (
            db.session.query(
                Tag,
                func.count(Post.id).label("post_count"),
            )
            .join(post_tags, post_tags.c.tag_id == Tag.id)
            .join(Post, Post.id == post_tags.c.post_id)
            .filter(
                Post.is_published.is_(True),
                Post.status == "published",
            )
            .group_by(Tag.id)
            .order_by(
                func.count(Post.id).desc(),
                Tag.id.asc(),
            )
            .limit(10)
            .all()
        )

    popular_tag_rows = get_cached_value(
        "public_popular_tags",
        timeout=300,
        loader=load_popular_tags,
    )

    # Keep popular_tags as a list of Tag objects for the template.
    popular_tags = [
        tag
        for tag, post_count in popular_tag_rows
    ]

    # --------------------------------------------------
    # 7. SUPERIOR ADS
    # Keep ad selection and tracking context request-specific.
    # --------------------------------------------------
    homepage_banner_ad = get_superior_ad(
        placement="homepage_banner",
    )

    sidebar_ad = get_superior_ad(
        placement="sidebar",
    )

    homepage_banner_context = None
    sidebar_context = None

    if homepage_banner_ad:
        homepage_banner_context = make_ad_tracking_context(
            homepage_banner_ad,
            publisher="superior-news",
            placement="homepage_banner",
        )

    if sidebar_ad:
        sidebar_context = make_ad_tracking_context(
            sidebar_ad,
            publisher="superior-news",
            placement="sidebar",
        )

    # --------------------------------------------------
    # 8. RENDER HOMEPAGE
    # --------------------------------------------------
    return render_template(
        "homepage.html",
        posts=posts,
        popular_posts=popular_posts,
        popular_tags=popular_tags,
        latest_posts=latest_posts,
        category_sections=today_categories,
        homepage_banner_ad=homepage_banner_ad,
        sidebar_ad=sidebar_ad,
        homepage_banner_context=homepage_banner_context,
        sidebar_context=sidebar_context,
        breaking_posts=breaking_posts,
        Post=Post,
        form=form,
    )

@public_bp.route("/post/<slug>", endpoint='post_detail')
def post_detail(slug):
    if not slug or slug.lower() in {"none", "null", "undefined"}:
        current_app.logger.warning(
            "Invalid article slug requested: %r | Referer: %r",
            slug,
            request.referrer,
        )
        abort(404)

    two_days_ago = datetime.utcnow() - timedelta(days=2)
    form = SubscribeForm()
    post = Post.query.filter(
        Post.slug == slug,
        Post.is_published.is_(True),
        Post.status == "published",
    ).first_or_404()
  
    # ---------------------------
    # VIEW COUNT (SAFE)
    # ---------------------------
    session_id = session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        session["session_id"] = session_id

    # Get user IP (simple way)
    ip_address = request.remote_addr

    # Check if this session/user/IP has already viewed this post
    view_cutoff = datetime.now(UTC) - timedelta(hours=24)

    already_viewed = (
        db.session.query(PageView.id)
        .filter(
            PageView.path == f"/post/{slug}",
            PageView.session_id == session_id,
            PageView.created_at >= view_cutoff,
        )
        .first()
    )
  
    if not already_viewed:
        # Increment post view count
        post.views = (post.views or 0) + 1
        db.session.add(PageView(
            user_id=getattr(current_user, "id", None),
            session_id=session_id,
            path=f"/post/{slug}",
            ip_address=ip_address,
            created_at=datetime.now(UTC)
        ))
        safe_commit()

    # ---------------------------
    # CATEGORY-BASED RELATED + TRENDING
    # ---------------------------
    related_posts = (
        Post.query
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
            Post.category_id == post.category_id,
            Post.id != post.id,
            Post.published_at >= two_days_ago,
            Post.slug.isnot(None),
            Post.slug != "",
        )
        .order_by(
            desc(
                func.coalesce(Post.views, 0)
                + func.coalesce(Post.like_count, 0)
                + func.coalesce(Post.related_clicks, 0)
            )
        )
        .limit(5)
        .all()
    )
    
    # Dynamic title
    if related_posts and related_posts[0].views >= 1000:
        section_title = "Trending in This Category"
    else:
        section_title = "Related Stories"
  
    content_html = inject_inpost_content(
        post.content,
        category=post.category.name if post.category else None,
    )
  
    return render_template("post.html", post=post, content_html=content_html, related_posts=related_posts, form=form, section_title=section_title)

@public_bp.route("/track-related-click", methods=["POST"])
def track_related_click():
    data = request.get_json()
    post = Post.query.get(data["post_id"])
    if post:
        post.related_clicks = (post.related_clicks or 0) + 1
        if not safe_commit():
          print("Failed to view related posts")
    return {"status": "ok"}

# Add comment
@public_bp.route('/comment/<slug>', methods=['POST'])
@login_required
def add_comment(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    content = request.form['content']
    comment = Comment(content=content, user_id=current_user.id, post_id=post.id)
    db.session.add(comment)
    if not safe_commit():
        print("Failed to add comment")

    # Check if AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "username": current_user.username,
            "content": content,
            "created_at": comment.created_at.strftime('%b %d, %Y %H:%M'),
            "reply_url": url_for("public.add_reply", comment_id=comment.id),
            "csrf_token": (generate_csrf() if "generate_csrf" in globals() else "")
        })
    flash("Comment posted!", "success")
    return redirect(url_for('public.post_detail', slug=slug))

# Add reply
@public_bp.route('/reply/<int:comment_id>', methods=['POST'])
@login_required
def add_reply(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    content = request.form['content']
    reply = Reply(content=content, user_id=current_user.id, comment_id=comment.id)
    db.session.add(reply)
    if not safe_commit():
        print("Failed to add reply")
    return jsonify({
        "username": current_user.username,
        "content": reply.content,
        "created_at": reply.created_at.strftime("%b %d, %Y %H:%M")
    })

@public_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()[:150]

    page = request.args.get("page", 1, type=int)
    page = max(page, 1)

    results = None

    if query:
        search_filter = or_(
            Post.title.ilike(f"%{query}%"),
            Post.content.ilike(f"%{query}%"),
        )

        results = (
            Post.query
            .filter(
                Post.is_published.is_(True),
                Post.status == "published",
                search_filter,
            )
            .order_by(Post.created_at.desc())
            .paginate(
                page=page,
                per_page=15,
                error_out=False,
            )
        )

    return render_template(
        "search.html",
        query=query,
        results=results,
    )

@public_bp.route("/load-more")
def load_more():
    page = max(
        request.args.get("page", 1, type=int),
        1,
    )

    pagination = (
        Post.query
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
        )
        .order_by(Post.created_at.desc())
        .paginate(
            page=page,
            per_page=5,
            error_out=False,
        )
    )

    if not pagination.items:
        return jsonify({
            "html": "",
            "has_more": False,
        })

    html = render_template(
        "post_cards.html",
        posts=pagination.items,
    )

    return jsonify({
        "html": html,
        "has_more": pagination.has_next,
    })

@public_bp.route("/pricing", endpoint="pricing")
def pricing_page():
    return render_template("pricing.html")

@public_bp.route("/subscribe", methods=["POST"])
def subscribe():
    form = SubscribeForm()

    if not form.validate_on_submit():
        flash("Invalid email submission.", "error")
        return redirect(request.referrer)

    email = form.email.data.lower().strip()

    if not email:
        flash("Please enter an email address.", "error")
        return redirect(request.referrer)

    existing = Subscriber.query.filter_by(email=email).first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
        flash("You're already subscribed", "info")
        return redirect(request.referrer)

    token = secrets.token_urlsafe(32)

    subscriber = Subscriber(
        email=email,
        unsubscribe_token=token, 
        is_active=True
    )

    db.session.add(subscriber)
    if not safe_commit():
        print("Failed to add subscribers")
        flash("Something went wrong. Try again.", "error")
        return redirect(request.referrer)

    # ✅ SEND WELCOME EMAIL HERE
    send_welcome_email(email, token)

    flash("Thanks for subscribing", "success")
    return redirect(request.referrer)

@public_bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    subscriber = Subscriber.query.filter_by(
        unsubscribe_token=token
    ).first_or_404()

    subscriber.is_active = False

    if not safe_commit():
        current_app.logger.error(
            "Failed to unsubscribe %s",
            subscriber.email,
        )

        return (
            "Error unsubscribing. Please try again.",
            500,
        )

    flash(
        f"You have been unsubscribed successfully. {subscriber.email}",
        "success",
    )

    return redirect(url_for("public.index"))

@public_bp.route("/tag/<string:slug>")
def tag(slug):
    tag = Tag.query.filter_by(
        slug=slug
    ).first_or_404()

    page = max(
        request.args.get("page", 1, type=int),
        1,
    )

    posts = (
        Post.query
        .filter(
            Post.tags.any(Tag.id == tag.id),
            Post.is_published.is_(True),
            Post.status == "published",
        )
        .order_by(
            Post.created_at.desc(),
            Post.id.desc(),
        )
        .paginate(
            page=page,
            per_page=15,
            error_out=False,
        )
    )

    return render_template(
        "tag.html",
        tag=tag,
        posts=posts,
    )

@public_bp.route("/category/<string:slug>")
def category(slug):
    form = SubscribeForm()

    category = (
        Category.query
        .filter_by(slug=slug)
        .first_or_404()
    )

    page = max(
        request.args.get("page", 1, type=int),
        1,
    )

    # --------------------------------------------------
    # 1. CATEGORY ARTICLE PAGINATION
    # --------------------------------------------------
    posts = (
        Post.query
        .filter(
            Post.category_id == category.id,
            Post.is_published.is_(True),
            Post.status == "published",
        )
        .order_by(Post.created_at.desc())
        .paginate(
            page=page,
            per_page=15,
            error_out=False,
        )
    )

    # --------------------------------------------------
    # 2. SUPERIOR ADS
    # --------------------------------------------------
    homepage_banner_ad = get_superior_ad(
        placement="homepage_banner",
    )

    sidebar_ad = get_superior_ad(
        placement="sidebar",
    )

    homepage_banner_context = (
        make_ad_tracking_context(
            homepage_banner_ad,
            publisher="superior-news",
            placement="homepage_banner",
        )
        if homepage_banner_ad
        else None
    )

    sidebar_context = (
        make_ad_tracking_context(
            sidebar_ad,
            publisher="superior-news",
            placement="sidebar",
        )
        if sidebar_ad
        else None
    )

    # --------------------------------------------------
    # 3. TRENDING POSTS
    # First identify articles with at least five comments.
    # --------------------------------------------------
    def load_trending_post_ids():
        comment_counts = (
            db.session.query(
                Comment.post_id.label("post_id"),
                func.count(Comment.id).label("comment_count"),
            )
            .join(Post, Post.id == Comment.post_id)
            .filter(
                Post.category_id == category.id,
                Post.is_published.is_(True),
                Post.status == "published",
            )
            .group_by(Comment.post_id)
            .having(func.count(Comment.id) >= 5)
            .subquery()
        )

        popularity_score = (
            func.coalesce(Post.views, 0)
            + func.coalesce(Post.like_count, 0)
            + func.coalesce(comment_counts.c.comment_count, 0)
        )

        rows = (
            db.session.query(Post.id)
            .join(
                comment_counts,
                comment_counts.c.post_id == Post.id,
            )
            .filter(
                Post.category_id == category.id,
                Post.is_published.is_(True),
                Post.status == "published",
            )
            .order_by(
                popularity_score.desc(),
                Post.created_at.desc(),
            )
            .limit(5)
            .all()
        )

        return [row[0] for row in rows]

    trending_cache_key = (
        f"public_category_trending_ids_{category.id}"
    )

    trending_ids = get_cached_value(
        trending_cache_key,
        timeout=60,
        loader=load_trending_post_ids,
    )

    # Retrieve the records in the same ranking order.
    if trending_ids:
        trending_records = (
            Post.query
            .filter(
                Post.id.in_(trending_ids),
                Post.category_id == category.id,
                Post.is_published.is_(True),
                Post.status == "published",
            )
            .all()
        )

        trending_by_id = {
            post.id: post
            for post in trending_records
        }

        trending_posts = [
            trending_by_id[post_id]
            for post_id in trending_ids
            if post_id in trending_by_id
        ]
    else:
        trending_posts = []

    # --------------------------------------------------
    # 4. CATEGORY VIEW COUNT
    # --------------------------------------------------
    category.views = (category.views or 0) + 1

    if not safe_commit():
        current_app.logger.warning(
            "Failed to increment category views for category %s",
            category.id,
        )

    # --------------------------------------------------
    # 5. RENDER CATEGORY PAGE
    # --------------------------------------------------
    return render_template(
        "category.html",
        category=category,
        posts=posts,
        form=form,
        homepage_banner_ad=homepage_banner_ad,
        sidebar_ad=sidebar_ad,
        homepage_banner_context=homepage_banner_context,
        sidebar_context=sidebar_context,
        trending_posts=trending_posts,
    )

@csrf.exempt
@public_bp.route("/post/<int:id>/like", methods=["POST"])
def like_post(id):
    post = Post.query.get_or_404(id)

    if "sid" not in session:
        session["sid"] = os.urandom(16).hex()

    existing = Like.query.filter_by(
        post_id=id,
        session_id=session["sid"]
    ).first()

    if existing:
        return jsonify({
            "liked": False,
            "count": Like.query.filter_by(post_id=id).count()
        })

    like = Like(
        post_id=id,
        session_id=session["sid"]
    )
    db.session.add(like)
    db.session.commit()

    count = Like.query.filter_by(post_id=id).count()

    return jsonify({
        "liked": True,
        "count": count
    })

# ----- CONTACT US -----
@public_bp.route("/contact", methods=["GET", "POST"])
@csrf.exempt
def contact():
    if request.method == "POST":
        msg = ContactMessage(
            name=request.form.get("name", "Anonymous"),
            email=request.form.get("email", "anonymous@superiornews.app"),
            subject=request.form.get("subject", "Feedback"),
            message=request.form.get("message", ""),
            type=request.form.get("type", "feedback")  # contact | feedback | report
        )

        db.session.add(msg)
        success = safe_commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True})
  
        if success:
            flash("Your message has been sent successfully.", "success")
        else:
            flash("Failed to send message. Please try again.", "error")
        return redirect(url_for("public.contact"))

    return render_template("contact.html")

@public_bp.route("/contact_feedback", methods=["GET", "POST"])
@csrf.exempt
def contact_feedback():
    if request.method == "POST":
        content = request.form.get("message", "").strip()

        if not content:
            flash("Feedback cannot be empty.", "error")
            return redirect(url_for("public.index"))
    
        if len(content) < 10:
            flash("Feedback must be at least 10 characters.", "error")
            return redirect(url_for("public.index"))
    
        if len(content) > 1000:
            flash("Feedback is too long.", "error")
            return redirect(url_for("public.index"))
        msg = ContactMessage(
            name=request.form.get("name", "Anonymous"),
            email=request.form.get("email", "anonymous@superiornews.app"),
            subject=request.form.get("subject", "Feedback"),
            message=content,
            type=request.form.get("type", "feedback")
        )

        db.session.add(msg)
        success = safe_commit()

        if success:
            flash("Thank you! Your feedback has been submitted.", "success")
        else:
            flash("Failed to send feedback. Please try again.", "error")

        return redirect(url_for("public.index"))

    return render_template("contact.html")

# ----- ABOUT -----
@public_bp.route("/about")
def about():
    settings = AppSettings.query.first()
    return render_template("about.html", settings=settings)

@public_bp.route("/disclaimer")
def disclaimer():
    return render_template("user/disclaimer.html")

# ----- PRIVACY -----
@public_bp.route("/privacy")
def privacy():
    settings = AppSettings.query.first()
    return render_template("privacy.html", settings=settings)

@public_bp.route("/terms")
def terms():
    settings = AppSettings.query.first()
    return render_template("terms.html", settings=settings)

def safe_date(dt):
    if not dt:
        return datetime.utcnow()
    if isinstance(dt, str):
        return datetime.fromisoformat(dt)
    return dt

def safe_date(dt):
    if not dt:
        return datetime.utcnow()

    if isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt)
        except ValueError:
            return datetime.utcnow()

    return dt


@public_bp.route("/sitemap.xml")
@cache.cached(timeout=3600)
def sitemap():
    pages = []

    pages.append({
        "loc": url_for(
            "public.index",
            _external=True,
        ),
        "lastmod": datetime.utcnow(),
    })

    categories = Category.query.order_by(Category.id).all()

    for category in categories:
        pages.append({
            "loc": url_for(
                "public.category",
                slug=category.slug,
                _external=True,
            ),
            "lastmod": datetime.utcnow(),
        })

    posts = (
        Post.query
        .filter(
            Post.is_published.is_(True),
            Post.status == "published",
        )
        .order_by(Post.created_at.desc())
        .limit(45000)
        .all()
    )

    for post in posts:
        pages.append({
            "loc": url_for(
                "public.post_detail",
                slug=post.slug,
                _external=True,
            ),
            "lastmod": safe_date(
                post.updated_at or post.created_at
            ),
            "title": post.title,
        })

    response = make_response(
        render_template(
            "sitemap.xml",
            pages=pages,
        ),
        200,
    )

    response.headers["Content-Type"] = "application/xml; charset=utf-8"

    return response