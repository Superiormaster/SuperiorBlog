from flask import (
    Blueprint, render_template, request,
    redirect, current_app, url_for, flash, jsonify
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from app.extensions import cache
from markupsafe import escape, Markup
from sqlalchemy import or_, func, cast, Integer
from app.utils.db_helpers import safe_commit
from app.utils.cloudinary_helper import upload_image_file, allowed_file
from app.utils.email import send_email
from app.models import Post, AppSettings, User, ContactMessage, Repost, Subscriber, DigestDraft, Ad, XPost, BreakingNews, Tag, Comment, PageView, EmailCampaign, CampaignRecipient
from app.extensions import db, csrf
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.admin_analytics_cache import get_admin_analytics
from app.utils.admin_email import *
from app.utils.analytics import analytics_block, get_range, percentage_growth, safe_list, active_users_by_day, active_users, track_login
from werkzeug.utils import secure_filename
from slugify import slugify
import os
from datetime import datetime, timedelta
from app.forms import LoginForm, PostForm, ChangePasswordForm, AdminTribeForm, RemoveTribeForm

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

    page = max(request.args.get("page", 1, type=int), 1)
    query_text = request.args.get("q", "").strip()[:150]
    status = request.args.get("status", "all").lower()

    query = Post.query

    if query_text:
        query = query.filter(
            Post.title.ilike(f"%{query_text}%")
        )

    allowed_statuses = {
        "published",
        "draft",
        "pending",
        "rejected",
    }

    if status in allowed_statuses:
        query = query.filter(Post.status == status)
    else:
        status = "all"

    posts = (
        query
        .order_by(Post.created_at.desc())
        .paginate(
            page=page,
            per_page=10,
            error_out=False,
        )
    )

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        q=query_text,
        status=status,
    )

@admin_bp.route("/admin/post/<int:id>")
@login_required
def view_post(id):

    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    post = Post.query.get_or_404(id)

    tribe_form = AdminTribeForm(
        data={
            "tribe_url": post.tribe_url or "",
            "tribe_title": post.tribe_title or "",
            "tribe_description": post.tribe_description or "",
            "tribe_button_text": post.tribe_button_text or "",
        }
    )

    remove_tribe_form = RemoveTribeForm()

    return render_template(
        "admin/pending.html",
        post=post,
        tribe_form=tribe_form,
        remove_tribe_form=remove_tribe_form
    )

@admin_bp.route("/admin/post/<int:id>/tribe/remove", methods=["POST"])
@login_required
def remove_post_tribe(id):

    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    post = Post.query.get_or_404(id)

    form = RemoveTribeForm()

    if form.validate_on_submit():

        post.tribe_url = None
        post.tribe_title = None
        post.tribe_description = None
        post.tribe_button_text = None

        try:
            safe_commit()
            flash(
                "Tribe conversation removed successfully.",
                "success"
            )

        except Exception as e:
            db.session.rollback()

            print(
                "Remove Tribe error:",
                str(e)
            )

            flash(
                "Failed to remove Tribe conversation.",
                "danger"
            )

    return redirect(
        url_for("admin.view_post", id=post.id)
    )

@admin_bp.route("/admin/post/<int:id>/tribe", methods=["POST"])
@login_required
def update_post_tribe(id):

    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    post = Post.query.get_or_404(id)

    form = AdminTribeForm()

    if form.validate_on_submit():

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

        try:
            safe_commit()

            flash(
                "Tribe conversation updated successfully.",
                "success"
            )

        except Exception as e:
            db.session.rollback()

            print(
                "Tribe update error:",
                str(e)
            )

            flash(
                "Failed to update Tribe conversation.",
                "danger"
            )

    else:

        for field, errors in form.errors.items():
            for error in errors:
                flash(
                    f"{field}: {error}",
                    "danger"
                )

    return redirect(
        url_for(
            "admin.view_post",
            id=post.id
        )
    )

@admin_bp.route("/post/<int:id>/approve", methods=["POST"])
@admin_bp.route("/approve/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
def approve_post(id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))
  
    post = Post.query.get_or_404(id)

    post.status = "published"
    post.is_published = True
    post.rejection_reason = None
    post.published_at = datetime.utcnow()
    post.is_locked = True

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
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))
  
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

def get_page(default=1):
    return max(
        request.args.get("page", default, type=int) or default,
        1,
    )

@admin_bp.route("/admin/subscribers")
@login_required
def list_subscribers():
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    page = get_page()

    pagination = (
        Subscriber.query
        .order_by(Subscriber.created_at.desc())
        .paginate(
            page=page,
            per_page=25,
            error_out=False,
        )
    )

    counts = db.session.query(
        func.count(Subscriber.id).label("total"),
        func.sum(
            db.case(
                (Subscriber.is_active.is_(True), 1),
                else_=0,
            )
        ).label("active"),
        func.sum(
            db.case(
                (Subscriber.is_active.is_(False), 1),
                else_=0,
            )
        ).label("inactive"),
    ).one()

    return render_template(
        "admin/subscribers.html",
        subscribers=pagination.items,
        pagination=pagination,
        total_subscribers=counts.total or 0,
        active_subscribers=counts.active or 0,
        unsubscribed=counts.inactive or 0,
    )

@admin_bp.route('/admin/subscriber/<int:id>/toggle-digest', methods=['POST'])
@csrf.exempt
def toggle_digest(id):
    subscriber = Subscriber.query.get_or_404(id)
    subscriber.receive_digest = not subscriber.receive_digest
    if not safe_commit():
        print("Failed to reject post")

    flash("Subscriber preference updated")
    return redirect(url_for('admin.list_subscribers'))

@admin_bp.route('/admin/email/welcome/<int:id>', methods=['POST'])
@csrf.exempt
def resend_welcome(id):
    subscriber = Subscriber.query.get_or_404(id)
    send_welcome_email(subscriber.email, subscriber.unsubscribe_token)
    flash("Welcome email resent")
    return redirect(url_for('admin.list_subscribers'))

@admin_bp.route("/admin/drafts")
@login_required
def list_drafts():
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    pagination = (
        DigestDraft.query
        .order_by(DigestDraft.id.desc())
        .paginate(
            page=get_page(),
            per_page=20,
            error_out=False,
        )
    )

    return render_template(
        "admin/drafts.html",
        drafts=pagination.items,
        pagination=pagination,
    )

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

    subscriber = None

    subscriber_id = request.args.get("subscriber_id", type=int)

    if subscriber_id:
        subscriber = Subscriber.query.get_or_404(subscriber_id)

    if request.method == "POST":

        subject = request.form.get("subject")
        content = request.form.get("html_content")

        # Convert plain text to HTML
        content = (
            "<p>"
            + content.replace("\n\n", "</p><p>").replace("\n", "<br>")
            + "</p>"
        )

        # -----------------------------
        # Upload Image
        # -----------------------------
        image_file = request.files.get("image")
        image_url = request.form.get("image_url")

        if image_file and image_file.filename != "":

            if allowed_file(image_file.filename):

                uploaded_url = upload_image_file(
                  image_file,
                  folder="SuperiorNews/emails"
                )

                if uploaded_url:
                    image_url = uploaded_url

            else:
                flash("Invalid image type.", "danger")
                return redirect(request.url)

        # -----------------------------
        # Insert image into email
        # -----------------------------
        if image_url:
            content = f"""
            {content}
            <div style="text-align:center;margin-bottom:20px;">
                <img
                  src="{image_url}"
                  style="
                      display:block;
                      width:100%;
                      max-width:560px;
                      height:auto;
                      border-radius:8px;
                  ">
            </div>
            """

        draft = DigestDraft(
            subject=subject,
            html_content=content,
            audience=request.form.get("platform"),
            subscriber_id=subscriber.id if subscriber else None,
        )

        db.session.add(draft)

        if not safe_commit():
            flash("Failed to save draft", "danger")
            return redirect(request.url)

        flash("Draft saved", "success")

        return redirect(
            url_for(
                "admin.preview_draft",
                id=draft.id
            )
        )

    selected_platform = "superior_news"

    if subscriber:
      selected_platform = "single_email"

    return render_template(
        "admin/subscribers_draft.html",
        subscriber=subscriber,
        selected_platform=selected_platform
    )

@admin_bp.route("/admin/draft/<int:id>/create-campaign", methods=["POST"])
@login_required
@csrf.exempt
def create_draft_campaign_route(id):

    campaign = create_draft_campaign(id)

    if campaign is None:
        flash("Unable to create campaign.", "danger")
        return redirect(url_for("admin.list_drafts"))

    flash("Campaign created successfully.", "success")

    return redirect(
        url_for(
            "admin.campaign_details",
            id=campaign.id
        )
    )

@admin_bp.route("/admin/campaign/<int:id>/pause", methods=["POST"])
@login_required
@csrf.exempt
def pause_campaign_route(id):

    campaign = pause_campaign(id)

    if campaign is None:
        flash("Unable to pause campaign.", "danger")
    else:
        flash("Campaign paused.", "success")

    return redirect(
        url_for(
            "admin.campaign_details",
            id=id
        )
    )

@admin_bp.route("/admin/campaign/<int:id>/resume", methods=["POST"])
@login_required
@csrf.exempt
def resume_campaign_route(id):

    campaign = resume_campaign(id)

    if campaign is None:
        flash("Unable to resume campaign.", "danger")
    else:
        flash("Campaign resumed.", "success")

    return redirect(
        url_for(
            "admin.campaign_details",
            id=id
        )
    )

@admin_bp.route(
    "/admin/campaign/<int:id>/retry-failed",
    methods=["POST"]
)
@login_required
@csrf.exempt
def retry_failed_route(id):

    success = retry_failed_batch(id)

    if success:
        flash("Failed emails retried successfully.", "success")
    else:
        flash("Unable to retry campaign.", "danger")

    return redirect(
        url_for(
            "admin.campaign_details",
            id=id
        )
    )

@admin_bp.route("/send-breaking-digest", methods=["POST"])
@login_required
@csrf.exempt
def send_breaking_digest():

    campaign = create_breaking_campaign();

    if campaign is None:
        flash("Breaking News digest failed", "danger")
        return redirect(url_for("admin.list_campaigns"))
    
    flash("Breaking News digest created", "success")
    return redirect(
        url_for("admin.campaign_details", id=campaign.id)
    )

@admin_bp.route("/send-daily-digest", methods=["POST"])
@login_required
@csrf.exempt
def send_daily_digest():

    campaign = create_daily_campaign();

    if campaign is None:
        flash("Daily digest failed", "danger")
        return redirect(url_for("admin.list_campaigns"))
    
    flash("Daily digest created", "success")
    return redirect(
        url_for("admin.campaign_details", id=campaign.id)
    )

@admin_bp.route('/admin/email/send-digest', methods=['POST'])
@csrf.exempt
def send_digest():
    campaign = create_weekly_campaign()

    if campaign is None:
        flash("Weekly digest failed", "danger")
        return redirect(url_for("admin.list_campaigns"))
  
    flash("Weekly digest created", "success")
    return redirect(
        url_for("admin.campaign_details", id=campaign.id)
    )
  
# ==========================================
# CAMPAIGNS
# ==========================================
@admin_bp.route("/admin/campaigns")
@login_required
def list_campaigns():

    page = request.args.get("page", 1, type=int)

    campaigns = (
        EmailCampaign.query
        .order_by(EmailCampaign.created_at.desc())
        .paginate(
            page=page,
            per_page=10,
            error_out=False,
        )
    )

    return render_template(
        "admin/campaigns.html",
        campaigns=campaigns,
      )

@admin_bp.route("/admin/campaign/<int:id>")
@login_required
def campaign_details(id):

    campaign = EmailCampaign.query.get_or_404(id)

    # All batches
    batches = (
        db.session.query(CampaignRecipient.batch_number)
        .filter_by(campaign_id=id)
        .distinct()
        .order_by(CampaignRecipient.batch_number.asc())
        .all()
    )

    batch_list = []

    for batch in batches:

        number = batch.batch_number

        total, sent, failed = (
            db.session.query(
                func.count(CampaignRecipient.id),
                func.coalesce(
                    func.sum(
                        db.case(
                            (CampaignRecipient.status == "sent", 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        db.case(
                            (CampaignRecipient.status == "failed", 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .filter_by(
                campaign_id=id,
                batch_number=number,
            )
            .one()
        )

        if total == 0:
            status = "pending"
        elif sent + failed == total:
            status = "completed"
        elif sent or failed:
            status = "sending"
        else:
            status = "pending"

        batch_list.append({
            "number": number,
            "total": total,
            "sent": sent,
            "failed": failed,
            "status": status
        })

    failed_recipients = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=id,
            status="failed"
        )
        .order_by(CampaignRecipient.batch_number)
        .all()
    )

    timeline = []

    timeline.append({
        "time": campaign.created_at,
        "title": "Campaign Created"
    })

    for batch in batch_list:

        if batch["status"] in ("completed", "sending"):

            first = (
                CampaignRecipient.query
                .filter_by(
                    campaign_id=id,
                    batch_number=batch["number"]
                )
                .filter(
                    CampaignRecipient.sent_at.isnot(None)
                )
                .order_by(CampaignRecipient.sent_at.asc())
                .first()
            )

            if first:
                timeline.append({
                    "time": first.sent_at,
                    "title": f"Batch {batch['number']} Sent"
                })

    timeline.sort(
        key=lambda item: item["time"] or campaign.created_at
    )

    return render_template(
        "admin/campaign_details.html",
        campaign=campaign,
        batches=batch_list,
        failed_recipients=failed_recipients,
        timeline=timeline,
    )

@admin_bp.route(
    "/admin/campaign/<int:id>/send-next-batch",
    methods=["POST"]
)
@login_required
@csrf.exempt
def send_next_batch_route(id):

    success = send_next_batch(id)

    if success:
        flash("Batch sent successfully.", "success")
    else:
        flash("Unable to send batch.", "danger")

    return redirect(
        url_for(
            "admin.campaign_details",
            id=id
        )
    )


@admin_bp.route(
    "/admin/campaign/<int:id>/batch/<int:number>"
)
@login_required
def campaign_batch(id, number):

    campaign = EmailCampaign.query.get_or_404(id)

    recipients = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=id,
            batch_number=number
        )
        .all()
    )

    return render_template(
        "admin/campaign_batch.html",
        campaign=campaign,
        batch_number=number,
        recipients=recipients
    )


@admin_bp.route(
    "/admin/campaign/<int:id>/failed"
)
@login_required
def campaign_failed(id):

    campaign = EmailCampaign.query.get_or_404(id)

    failed = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=id,
            status="failed"
        )
        .all()
    )

    return render_template(
        "admin/campaign_failed.html",
        campaign=campaign,
        failed=failed
    )

@admin_bp.route('/email-logs')
@login_required
def email_logs():
    page = request.args.get('page', 1, type=int)
    subject = request.args.get('subject', '')
    email_search = request.args.get('email', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = EmailLog.query

    # Filter by subject
    if subject:
        query = query.filter(EmailLog.subject.ilike(f"%{subject}%"))

    # Search by email
    if email_search:
        query = query.filter(EmailLog.email.ilike(f"%{email_search}%"))

    try:
        start_date_obj = (
            datetime.strptime(start_date, "%Y-%m-%d")
            if start_date else None
        )
    
        end_date_obj = (
            datetime.strptime(end_date, "%Y-%m-%d")
            if end_date else None
        )
    except ValueError:
        flash("Invalid date filter.", "danger")
        return redirect(url_for("admin.email_logs"))

    # Filter by date range
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(EmailLog.created_at >= start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(EmailLog.created_at <= end_date_obj)

    logs = (
        query
        .order_by(EmailLog.created_at.desc())
        .paginate(
            page=get_page(),
            per_page=20,
            error_out=False,
        )
    )

    return render_template("admin/email_logs.html", logs=logs,
        subject=subject,
        email_search=email_search,
        start_date=start_date,
        end_date=end_date)

@admin_bp.route("/messages")
@login_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)

@admin_bp.route("/messages/<int:id>/reply", methods=["POST"])
@login_required
@csrf.exempt
def reply_message(id):
    msg = ContactMessage.query.get_or_404(id)

    reply_text = request.form.get("reply")

    if not reply_text:
        flash("Reply message cannot be empty.", "danger")
        return redirect(url_for("admin.admin_messages"))

    html = Markup("<br>").join(
      escape(reply_text).splitlines()
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.7;color:#333;">
      {html}
    </div>
    """
  
    text = reply_text

    success = send_email(
        to=msg.email,
        subject=f"Re: {msg.subject or 'Your message'}",
        html_content=html,
        text_content=text
    )
    log_email(msg.email, msg.subject, success)

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
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    allowed_ranges = {7, 30, 90}

    range_days = request.args.get("range", 7, type=int)

    if range_days not in allowed_ranges:
        range_days = 7

    data = get_admin_analytics(range_days)

    growth_defaults = data["growth_defaults"]

    return render_template(
        "admin/analytics.html",
        range_days=range_days,
        **data,

        # Keep the existing template variables available.
        growth_percentage=growth_defaults,
        total_read_time_growth=growth_defaults,
        total_active_users_growth=growth_defaults,
        total_likes_growth=growth_defaults,
        total_replies_growth=growth_defaults,
        total_deleted_accounts_growth=growth_defaults,
        total_caption_users_growth=growth_defaults,
        total_repost_growth=growth_defaults,
        total_impressions_growth=growth_defaults,
        total_profile_visits_growth=growth_defaults,
        total_shares_growth=growth_defaults,
        total_engagements_growth=growth_defaults,
        total_engagement_rate_growth=growth_defaults,
        total_time_on_page_growth=growth_defaults,
        unique_visitors_growth=growth_defaults,
    )

# ---------- LIST ADS ----------
@admin_bp.route("/ads")
@login_required
def ads_list():
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    pagination = (
        Ad.query
        .order_by(
            Ad.priority.desc(),
            Ad.created_at.desc(),
        )
        .paginate(
            page=max(request.args.get("page", 1, type=int) or 1, 1),
            per_page=12,
            error_out=False,
        )
    )

    return render_template(
        "admin/ads_list.html",
        ads=pagination.items,
        pagination=pagination,
    )

def upload_to_cloudinary(file, width,
    height=200):
    """
    Upload a Flask FileStorage object to Cloudinary and return the secure URL.
    """
    try:
        return upload_image_file(file, folder="SuperiorNews/ads", crop_for_ads=True, width=width, height=200)
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload failed: {e}")
        return None

# ---------- CREATE NEW AD ----------
@admin_bp.route("/ads/form", methods=["GET", "POST"])
@admin_bp.route("/ads/form/<int:ad_id>", methods=["GET", "POST"])
@login_required
def ad_form(ad_id=None):

    ad = Ad.query.get(ad_id) if ad_id else None

    if request.method == "POST":

        ad_location = request.form["location"]

        ad_width_value = request.form.get("ad_width")
        
        if ad_location == "full_page":
            ad_width = None
        else:
            ad_width = int(ad_width_value) if ad_width_value else 600

        # Upload image if provided
        image_file = request.files.get("image")
        image_url = request.form.get("image_url") or (ad.image_url if ad else None)

        if image_file and image_file.filename != "":
          if allowed_file(image_file.filename):
      
              if ad_location == "full_page":
                  uploaded_url = upload_image_file(
                    image_file,
                    folder="SuperiorNews/media"
                  )
              else:
                  uploaded_url = upload_to_cloudinary(
                      image_file,
                      width=ad_width
                  )
      
              if uploaded_url:
                  image_url = uploaded_url
          else:
              flash("Invalid image type.", "danger")
              return redirect(request.url)

        if not ad:
            ad = Ad()
            db.session.add(ad)

        # Assign fields
        ad.name = request.form["name"]
        ad.title = request.form.get("title")
        ad.image_url = image_url
        ad.target_url = request.form.get("target_url")
        ad.html_code = request.form.get("html_code")
        ad.type = request.form.get("type", "custom")
        ad.internal = "internal" in request.form
        ad.location = request.form["location"]
        ad.priority = int(request.form.get("priority", 1))
        ad.active = "active" in request.form

        safe_commit()

        flash(
            "Ad updated successfully!" if ad_id else "Ad created successfully!",
            "success"
        )
        return redirect(url_for("admin.ads_list"))

    return render_template("admin/create_media.html", ad=ad)

# ---------- DELETE AD ----------
@admin_bp.route("/ads/delete/<int:ad_id>", methods=["POST"])
@login_required
def delete_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    db.session.delete(ad)
    safe_commit()
    flash("Ad deleted successfully!", "success")
    return redirect(url_for("admin.ads_list"))

@admin_bp.route("/click/<int:ad_id>")
def ad_click(ad_id):
    ad = Ad.query.get_or_404(ad_id)

    target = ad.target_url.strip()

    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    return redirect(target)

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
@csrf.exempt
@login_required
def delete(id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for("public.user_login"))

    post = Post.query.get_or_404(id)

    try:
        db.session.delete(post)

        if not safe_commit():
            db.session.rollback()
            flash("Failed to delete post.", "danger")
        else:
            flash("Post deleted successfully.", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete post")
        flash("An error occurred while deleting the post.", "danger")

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
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    sort = request.args.get("sort", "newest")

    query = User.query

    # 🔎 Search
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    # 🔃 Sorting
    if sort == "oldest":
        query = query.order_by(User.created_at.asc())
    else:
        query = query.order_by(User.created_at.desc())

    users_paginated = query.paginate(page=page, per_page=10)

    return render_template(
        "admin/users.html",
        users=users_paginated,
        search=search,
        sort=sort
    )

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