from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, current_app, flash, make_response
from app.models import Post, Comment, Like, Subscriber, ContactMessage, CaptionHistory, Reply, Category, User, AppSettings, Tag, post_tags, Label, ProfileVisit, FootballCache, PageView
import os, traceback, re, base64, requests, secrets, uuid
from requests.exceptions import ConnectionError
from sqlalchemy import distinct, func, or_, and_
from uuid import uuid4
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime, UTC, timedelta
from app.moderation.engine import auto_moderate
from cloudinary.exceptions import Error as CloudinaryError
from app.moderation.rules import CATEGORY_RULES
from app.moderation.spam import is_spam
from app.moderation.grammar import grammar_score
from app.moderation.duplicate import is_duplicate
from app.utils.helper import process_tags, get_related_posts, publish_scheduled_posts
from app.utils.cloudinary_helper import upload_image_file
from app.utils.email import send_email
from app.utils.decorators import generate_unique_slug
from app.utils.db_helpers import safe_commit
from app.extensions import db, cache, csrf
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from oauthlib.oauth2 import WebApplicationClient
from sqlalchemy import func, desc
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import UserLoginForm, UserRegisterForm, ChangePasswordForm, PostForm, ProfileForm, DeletePostForm, SubmitPostForm, ResetPasswordForm, ForgotPasswordForm

public_bp = Blueprint(
    "public",
    __name__, 
    template_folder="../templates/user"
)

def track_login(user):
    user.login_count = (user.login_count or 0) + 1
    user.last_login = datetime.now(UTC)
    safe_commit()

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
        if not safe_commit():
          print("Failed to register user")
        flash("Account created! Please log in.", "success")
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
    if current_user.profile_completed:
        return redirect(url_for("public.user_dashboard"))

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        current_user.profile_completed = True
        if not safe_commit():
          print("Failed to setup profile")

        flash("Profile completed successfully", "success")
        return redirect(url_for("public.user_dashboard"))

    return render_template(
        "user/profile_setup.html",
        form=form,
        user=current_user
    )

@public_bp.route("/profile/<username>")
@login_required
@csrf.exempt
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_owner = current_user.id == user.id

    # log the visit
    visit = ProfileVisit(
        visited_user_id=username,
        visitor_id=current_user.id if current_user.is_authenticated else None
    )
    db.session.add(visit)
    if not safe_commit():
        print("Failed to add visit")

    return render_template(
        "user/profile.html",
        user=user,
        is_owner=is_owner
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

@public_bp.route('/analysis')
@login_required
def user_analysis():
    range_days = request.args.get("range", "30")
    now = datetime.utcnow()

    if range_days == "7":
        start_date = now - timedelta(days=7)
    elif range_days == "30":
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    query = Post.query.filter_by(user_id=current_user.id)

    if start_date:
        query = query.filter(Post.created_at >= start_date)

    posts = query.all()
    no_of_posts = len(posts)

    total_views = sum(p.views or 0 for p in posts)
    total_likes = sum(p.likes.count() for p in posts)
    total_read_time = sum(p.read_time or 0 for p in posts)
    avg_read_time = sum(p.read_time or 0 for p in posts)
    profile_visits = ProfileVisit.query.filter_by(
        visited_user_id=current_user.id
    ).count()
    total_shares = sum(p.shares or 0 for p in posts)
    total_replies = sum(len(c.replies) for p in posts for c in p.comments)

    # Avg per post
    avg_read_time = round(total_read_time / no_of_posts, 2) if no_of_posts else 0

    # ✅ Average time per view
    if total_views > 0:
        avg_time_per_view = round(total_read_time / total_views, 2)
    else:
        avg_time_per_view = 0

    # Previous period
    previous_views = previous_likes = previous_read_time =  previous_posts_count = 0
    engagement_rate = 0
    previous_shares = 0
    previous_avg_read_time = previous_engagement_rate = 0
    engagement_rate_growth = 0
    previous_profile_visits = previous_total_replies = previous_total_shares = 0
    if start_date:
        period_length = now - start_date
        prev_start = start_date - period_length
        previous_posts = Post.query.filter(
            Post.user_id == current_user.id,
            Post.created_at >= prev_start,
            Post.created_at < start_date
        ).all()
        previous_views = sum(p.views or 0 for p in previous_posts)
        previous_likes = sum(p.likes.count() for p in previous_posts) if start_date else 0
        previous_read_time = sum(p.read_time or 0 for p in previous_posts) if start_date else 0
        previous_total_shares = sum(p.shares or 0 for p in previous_posts)
        previous_profile_visits = ProfileVisit.query.filter(
            ProfileVisit.visited_user_id == current_user.id,
            ProfileVisit.created_at >= prev_start,
            ProfileVisit.created_at < start_date
        ).count()
        previous_total_replies = sum(
            len(c.replies) for p in previous_posts for c in p.comments
        )
        previous_total_engagements = previous_likes + previous_total_replies + previous_total_shares
        previous_engagement_rate = round((previous_total_engagements / previous_views) * 100, 2) if previous_views else 0
        previous_posts_count = len(previous_posts) if start_date else 0
    else:
        previous_views = previous_likes = previous_read_time = previous_posts_count = 0

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
    avg_read_time_growth = calculate_growth(avg_read_time, previous_avg_read_time)
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

    for p in posts:
        if p.created_at:
            day = p.created_at.strftime("%Y-%m-%d")
            daily_views[day] += p.views or 0
            daily_likes[day] += p.likes.count()

    chart_labels = sorted(daily_views.keys())
    views_data = [daily_views[d] for d in chart_labels]
    likes_data = [daily_likes[d] for d in chart_labels]

    return render_template(
        "user/analysis.html",
        total_views=total_views,
        total_likes=total_likes,
        total_read_time=total_read_time,
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
        
        engagements_growth=likes_growth,
        impressions_growth=views_growth,
        shares_growth=shares_growth
    )

@public_bp.route("/post/<int:post_id>/share", methods=["POST"])
@login_required
@csrf.exempt
def share_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.shares = (post.shares or 0) + 1
    if not safe_commit():
        print("Failed to share post")
    return {"success": True}

@public_bp.route('/dashboard')
@login_required
def user_dashboard():
    all_user_posts = Post.query.filter_by(user_id=current_user.id).all()

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
            return render_template("user/create.html", form=form, rules=rules, post=post)

        db.session.add(post)
        if not safe_commit():
          print("Failed to save post")

        try:
          result = auto_moderate(post, current_user) if post else None
          status = result["status"]
          reason = result.get("reason")
  
          if status == "rejected":
              post.status = "rejected"
              flash(reason, "error")
              if not safe_commit():
                print("Failed to save post")
              return redirect(url_for("public.edit_post", id=post.id))
          
          if status == "pending_review":
              post.status = "pending_review"
              flash(reason or "Post requires editorial review", "warning")
              if not safe_commit():
                print("Failed to save post")
              return redirect(url_for("public.user_dashboard"))
          # ✅ Auto-approve
          post.status = "approved"
          post.is_published = False
        except ConnectionError:
          # Handle network issues gracefully
          flash("⚠️ Network error: Unable to reach the moderation service. Please check your internet connection.", "error")
          result = None  # Or handle as you need
        
        # ✅ ONLY approved posts reach here
        submit_status = request.form.get("status", "draft")

        # FEATURED IMAGE (ALWAYS)
        if not post.featured_image and post.content:
            soup = BeautifulSoup(post.content, "html.parser")
            first_img = soup.find("img")
            if first_img:
                post.featured_image = first_img.get("src")

        if submit_status == "published":
            post.status = "published"
            post.is_published = True
            post.published_at = datetime.utcnow()
            post.is_locked = True
        
        elif submit_status == "scheduled":
          scheduled_date = form.scheduled_at.data
          if not scheduled_date:
              flash("Please select a schedule date", "danger")
              return redirect(request.url)
          if not scheduled_date or scheduled_date <= datetime.utcnow():
              flash("The selected schedule date is not valid.", "danger")
              return redirect(request.url)
      
          post.status = "scheduled"
          post.scheduled_at = scheduled_date
          post.is_published = False
        
        else:
            post.status = "draft"
            post.is_published = False
            post.content = form.content.data
        
        if not safe_commit():
          print("Failed to save post")

        flash("Post submitted successfully.", "success")
        return redirect(url_for("public.user_dashboard"))

    return render_template(
        "user/create.html",
        form=form,
        post=post,
        rules=rules,
        moderation_status=status if post else None,
        moderation_reason=reason if post else None,
        existing_tags=[t.name for t in post.tags] if post and post.id else []
    )

@public_bp.route("/post/draft", methods=["POST"])
@csrf.exempt
@login_required
def save_draft():
    content = request.form.get("content", "").strip()
    if not content:
        return jsonify({"status": "ignored"})

    # Save draft logic here
    post_id = request.form.get("post_id")

    # Update existing post
    if post_id:
        post = Post.query.get(post_id)
        if not post or post.user_id != current_user.id:
            return jsonify({"status": "forbidden"})
        if getattr(post, "is_locked", False):
            return jsonify({"status": "locked"})
        post.content = content
        post.status = "draft"
        if not safe_commit():
            print("Failed to save post")
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

@public_bp.route("/post/user/<int:id>/submit", methods=["POST"])
@login_required
def submit_user_post(id):
    post = Post.query.get_or_404(id)

    # Can only submit own posts
    if post.user_id != current_user.id:
        flash("You cannot submit this post", "danger")
        return redirect(url_for("public.user_dashboard"))

    if post.status == "published":
        flash("Post is already published", "info")
        return redirect(url_for("public.user_dashboard"))
  
    if post.status not in ["draft", "rejected"]:
        flash("This post cannot be submitted", "warning")
        return redirect(url_for("public.user_dashboard"))

    if post.status == "rejected" and post.resubmission_count >= 2:
        flash("Maximum resubmissions reached", "danger")
        return redirect(url_for("public.user_dashboard"))

    if not post.content or len(post.content.strip()) < 50:
      flash("Post content is missing or too short", "danger")
      return redirect(url_for("public.user_dashboard"))

    try:
        result = auto_moderate(post, current_user)
        status = result["status"]           # this is now always defined
        reason = result.get("reason")
        post.status = status
        post.rejection_reason = reason
        post.is_published = (status == "published") 
        post.is_locked = True

        if status == "rejected":
            post.status = "rejected"
            flash(f"Post rejected: {reason}", "error")
        elif status == "pending_review":
            post.status = "pending_review"
            flash(f"Post requires editorial review: {reason or ''}", "warning")
        elif status == "approved":
            # ✅ Auto-publish if approved
            post.status = "published"
            post.is_published = True
            post.published_at = datetime.utcnow()
            flash("Post submitted and published successfully!", "success")

        # extract first image if no featured_image
        if not post.featured_image:
            soup = BeautifulSoup(post.content, "html.parser")
            first_img = soup.find("img")
            if first_img:
                post.featured_image = first_img.get("src")

        db.session.commit()
        flash(f"Post submitted: {status.upper()}" + (f" ({reason})" if reason else ""), "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error submitting post: {str(e)}", "danger")
        return redirect(url_for("public.user_dashboard"))

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
        print("Failed to delete post")
  
      flash("Post deleted successfully.", "success")
    return redirect(url_for("public.user_dashboard"))

@public_bp.route("/login/google")
def google_login():
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    redirect_uri = current_app.config["REDIRECT_URI"]
    # Google OAuth URL
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
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
    token_response = requests.post(token_url, data=data).json()
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
        user = User(email=user_email, username=f"user_{uuid4().hex[:8]}", oauth_provider="google", oauth_id=oauth_id, is_active=1, created_at=datetime.utcnow(), last_login=datetime.utcnow(), login_count=1,)
        db.session.add(user)
        if not safe_commit():
          print("Failed to login user")

    login_user(user)
    track_login(user)
    flash("Logged in successfully", "success")
    if user.profile_completed:
        return redirect(url_for("public.user_dashboard"))
    return redirect(url_for("public.profile_setup"))

@public_bp.route("/auth/google/onetap", methods=["POST"])
def google_one_tap():
    data = request.get_json()
    token = data.get("credential")

    if not token:
        return jsonify({"error": "No token provided"}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        return jsonify({"error": "Invalid token"}), 400

    # User info from Google
    email = idinfo["email"]
    name = idinfo.get("name")
    oauth_id = idinfo["sub"]
    picture = idinfo.get("picture")

    # Get or create user
    user = User.query.filter_by(oauth_id=oauth_id).first()
    if not user:
        user = User(
            email=email,
            username=name,
            oauth_provider="google",
            oauth_id=oauth_id,
            avatar=picture
        )
        db.session.add(user)
        if not safe_commit():
          print("Failed to login user")

    login_user(user)

    return jsonify({"success": True})

@public_bp.route('/logout')
def user_logout():
    logout_user()
    flash("You are logged out", "success")
    return redirect(url_for('public.index'))

@public_bp.route("/")
def index():
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)

    posts = (
        Post.query
        .filter(
            Post.is_published == True,
            Post.status == "published",
            Post.created_at >= seven_days_ago
        )
        .order_by(Post.created_at.desc())
        .all()
    )

    trending_posts = (
        Post.query
        .outerjoin(Comment)
        .filter(
            Post.is_published == True,
            Post.status == "published",
            Post.published_at >= three_days_ago,
            or_(
                Post.views >= 50,
                Post.like_count >= 10
            )
        )
        .group_by(Post.id)
        .having(func.count(Comment.id) >= 5)  # only aggregate needed in having
        .order_by((func.count(Comment.id) + Post.like_count + Post.views).desc())
        .limit(5)
        .all()
    )

    breaking_posts = (
        Post.query
        .join(Post.labels)
        .filter(
            Label.name.ilike("%breaking%"),
            Post.is_published == True,
            Post.status == "published",
            Post.published_at >= six_hours_ago
        )
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )

        # Get cached data
    live = FootballCache.query.filter_by(data_type="live", league="PL").first()
    table = FootballCache.query.filter_by(data_type="table", league="PL").first()

    live_matches = live.json_data if live else []

    league_table = []
    if table and isinstance(table.json_data, list) and len(table.json_data) > 0:
        league_table = table.json_data[0].get("table", [])

    popular_tags = (
        Tag.query
        .join(post_tags)
        .join(Post)
        .filter(Post.is_published == True)
        .group_by(Tag.id)
        .order_by(func.count(Post.id).desc())
        .limit(10)
        .all()
    )
    
    editor_picks = CaptionHistory.query \
        .filter(CaptionHistory.style == "editor_pick") \
        .order_by(desc(CaptionHistory.confidence)) \
        .limit(5).all()

    print("Live Matches:", live_matches)
    print("League Table:", league_table)
    return render_template("homepage.html", posts=posts, trending_posts=trending_posts, popular_tags=popular_tags, breaking_posts=breaking_posts, Post=Post, live_matches=live_matches, league_table=league_table, editor_picks=editor_picks)

@public_bp.route("/post/<slug>", endpoint='post_detail')
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    # Convert to HTML
    content_html = post.content
  
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
    already_viewed = PageView.query.filter(
        and_(
            PageView.path == f"/post/{slug}",
            PageView.session_id == session_id,
            PageView.created_at >= datetime.now(UTC) - timedelta(hours=24)
        )
    ).first()
  
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

    latest_posts = (
        Post.query
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .limit(5)
        .all()
    )

    # ---------------------------
    # CATEGORY-BASED RELATED + TRENDING
    # ---------------------------
    related_posts = (
        Post.query
        .filter(
            Post.is_published == True,
            Post.category_id == post.category_id,
            Post.id != post.id
        )
        .order_by(
            desc(Post.views + Post.like_count + Post.related_clicks)
        )
        .limit(5)
        .all()
    )
  
    # Dynamic title
    if related_posts and related_posts[0].views >= 1000:
        section_title = "Trending in This Category"
    else:
        section_title = "Related Stories"

    if not safe_commit():
        print("Failed to view post")

    return render_template("post.html", post=post, content_html=content_html, latest_posts=latest_posts, related_posts=related_posts, section_title=section_title)

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
@cache.cached(timeout=300)
def search():
    query = request.args.get("q", "")
    results = []

    if query:
        results = Post.query.filter(
            Post.is_published == True,
            Post.title.ilike(f"%{query}%") |
            Post.content.ilike(f"%{query}%")
        ).order_by(Post.created_at.desc()).all()

    return render_template("search.html", query=query, results=results)

@public_bp.route("/load-more")
def load_more():
    page = request.args.get("page", 1, type=int)

    pagination = (
        Post.query
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )
    data = get_posts_for_page(page)  # Your function to get data
    if not data:
        return jsonify({"error": "No more data"}), 404
    return jsonify(data)

    # ✅ STOP when no posts
    if not pagination.items:
        return jsonify({
            "html": "",
            "has_more": False
        })

    html = render_template(
        "post_cards.html",
        posts=pagination.items
    )

    return jsonify({
        "html": html,
        "has_more": pagination.has_next
    })

@public_bp.route("/pricing", endpoint="pricing")
def pricing_page():
    return render_template("pricing.html")

@public_bp.route("/subscribe", methods=["POST"])
@csrf.exempt
def subscribe():
    email = request.form.get("email")

    if not email:
        flash("Please enter a valid email address.", "error")
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

    flash("Thanks for subscribing", "success")
    return redirect(url_for("public.index"))

@public_bp.route('/unsubscribe/<token>')
def unsubscribe(token):
    subscriber = Subscriber.query.filter_by(unsubscribe_token=token).first_or_404()

    subscriber.is_active = False
    if not safe_commit():
      current_app.logger.error(f"Failed to unsubscribe {subscriber.email}")
      return "Error unsubscribing. Please try again.", 500

    return "You have been unsubscribed successfully. {subscriber.email}"

@public_bp.route("/tag/<string:slug>")
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()

    posts = Post.query.filter(
        Post.tags.contains(tag),
        Post.is_published == True
    ).order_by(Post.created_at.desc()).all()

    return render_template("tag.html", tag=tag, posts=posts)

@public_bp.route("/category/<string:slug>")
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()

    posts = (
        category.posts
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .all()
    )

    trending_posts = (
        Post.query
        .filter(
            Post.category_id == category.id,
            Post.is_published == True,
            Post.views >= 50,
            Post.like_count >= 10
        )
        .outerjoin(Post.comments)
        .group_by(Post.id)
        .having(func.count(Comment.id) >= 5)
        .order_by(
            desc(Post.views + Post.like_count + func.count(Comment.id))
        )
        .limit(5)
        .all()
    )

    category.views += 1
    if not safe_commit():
        print("Failed to view category post")

    return render_template(
        "category.html",
        category=category,
        posts=posts,
        trending_posts=trending_posts
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
            email=request.form.get("email", "anonymous@superiornewsw.app"),
            subject=request.form.get("subject", "Feedback"),
            message=request.form.get("content", ""),
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
        msg = ContactMessage(
            name=request.form.get("name", "Anonymous"),
            email=request.form.get("email", "anonymous@superiornews.app"),
            subject=request.form.get("subject", "Feedback"),
            message=request.form.get("content", ""),
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

# ----- PRIVACY -----
@public_bp.route("/privacy")
@cache.cached(timeout=300)
def privacy():
    settings = AppSettings.query.first()
    return render_template("privacy.html", settings=settings)

@public_bp.route("/terms")
@cache.cached(timeout=300)
def terms():
    settings = AppSettings.query.first()
    return render_template("terms.html", settings=settings)

# Sitemap for Google News
@public_bp.route("/sitemap.xml")
@cache.cached(timeout=300)
def sitemap():
    pages = []
    ten_days_ago = datetime.datetime.now() - datetime.timedelta(days=10)

    # Homepage & categories
    pages.append({"loc": url_for("public.index", _external=True), "lastmod": datetime.datetime.now()})
    for category in Category.query.all():
        pages.append({"loc": url_for("public.category", slug=category.slug, _external=True),
                      "lastmod": datetime.datetime.now()})

    # Posts
    posts = Post.query.filter(Post.is_published==True, Post.created_at >= ten_days_ago).all()
    for post in posts:
        pages.append({"loc": url_for("public.post_detail", slug=post.slug, _external=True),
                      "lastmod": post.updated_at})


    sitemap_xml = render_template("sitemap.xml", pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response