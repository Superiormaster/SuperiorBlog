# admin_email.py
from app.utils.email import send_email
from app.models import Subscriber, Post, BreakingNews, EmailLog, User, DigestDraft, EmailCampaign, CampaignRecipient
from flask import render_template
from app.extensions import db
from app.utils.db_helpers import safe_commit
import time
from math import ceil
from datetime import datetime, timedelta

def log_email(recipient, subject, success, subscriber=None):
    """
    Log the result of an email sent to a recipient.
    """

    log = EmailLog(
        subscriber_id=subscriber.id if subscriber else None,
        email=recipient,
        subject=subject,
        status="sent" if success else "failed",
    )

    db.session.add(log)

    if not safe_commit():
        print(f"Failed to log email for {recipient}")

    return log

def create_campaign(
    name,
    subject,
    html_content,
    campaign_type,
    batch_size=20,
):
    """
    Creates an email campaign and queues every active subscriber
    into batches.

    No emails are sent here.
    """

    subscribers = (
        Subscriber.query
        .filter_by(
            is_active=True,
            receive_digest=True
        )
        .order_by(Subscriber.id.asc())
        .all()
    )

    if not subscribers:
        return None

    campaign = EmailCampaign(
      name=name,
      subject=subject,
      html_content=html_content,
      campaign_type=campaign_type,
      status="pending",
      batch_size=batch_size,
      total_recipients=len(subscribers),
      sent_count=0,
      failed_count=0,
      completed_count=0,
      created_at=datetime.utcnow(),
    )

    db.session.add(campaign)
    db.session.flush()  # Get campaign.id before commit

    for index, subscriber in enumerate(subscribers):
        batch_number = (index // batch_size) + 1

        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            subscriber_id=subscriber.id,
            email=subscriber.email,
            batch_number=batch_number,
            status="pending",
        )

        db.session.add(recipient)

    total_batches = ceil(len(subscribers) / batch_size)

    if not safe_commit():
        print("Failed to create campaign")
        return None

    print(
        f"Campaign '{campaign.name}' created "
        f"({campaign.total_recipients} recipients, "
        f"{total_batches} batches)"
    )

    return campaign

def create_daily_campaign():
    """
    Create a Daily Digest campaign.

    Includes only posts published today.
    No emails are sent here.
    """

    now = datetime.utcnow()

    # Start of today
    start_of_day = datetime(
        now.year,
        now.month,
        now.day
    )

    posts = (
        Post.query
        .filter(
            Post.is_published == True,
            Post.published_at.isnot(None),
            Post.published_at >= start_of_day,
            Post.published_at <= now
        )
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )

    if not posts:
        return None

    html_content = render_template(
        "emails/daily_news.html",
        posts=posts,
        subscriber=None,
        now=now
    )

    campaign = create_campaign(
        name=f"Daily Digest {now.strftime('%B %d, %Y')}",
        subject="📰 Superior Daily News",
        html_content=html_content,
        campaign_type="daily",
    )

    return campaign


def create_weekly_campaign():
    """
    Create a Weekly Digest campaign.

    Includes only posts published within the last 7 days.
    No emails are sent here.
    """

    now = datetime.utcnow()

    # Last 7 days
    seven_days_ago = now - timedelta(days=7)

    posts = (
        Post.query
        .filter(
            Post.is_published == True,
            Post.published_at.isnot(None),
            Post.published_at >= seven_days_ago,
            Post.published_at <= now
        )
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )

    if not posts:
        return None

    html_content = render_template(
        "emails/weekly_digest.html",
        posts=posts,
        subscriber=None,
        now=now,
    )

    campaign = create_campaign(
        name=f"Weekly Digest {now.strftime('%B %d, %Y')}",
        subject="📰 Superior Weekly Digest",
        html_content=html_content,
        campaign_type="weekly",
    )

    return campaign

def create_breaking_campaign():
    """
    Create a Breaking News campaign.

    No emails are sent here.
    """

    yesterday = datetime.utcnow() - timedelta(days=1)

    news_items = (
        Post.query
        .filter(
            Post.is_breaking == True,
            Post.is_published == True,
            Post.published_at >= yesterday
        )
        .order_by(Post.published_at.desc())
        .all()
    )

    if not news_items:
        return None

    html_content = render_template(
        "emails/breaking_news.html",
        news_items=news_items,
        subscriber=None,
        now=datetime.utcnow(),
    )

    campaign = create_campaign(
        name=f"Breaking News {datetime.utcnow().strftime('%B %d, %Y %H:%M')}",
        subject="🚨 Breaking News",
        html_content=html_content,
        campaign_type="breaking",
    )

    return campaign

def refresh_campaign_content(campaign_id):
    """
    Refresh Daily or Weekly campaign content.

    Existing recipients, batches and delivery statuses remain unchanged.
    Only pending recipients will receive the refreshed content.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if not campaign:
        return False, "Campaign not found."

    if campaign.campaign_type not in ("daily", "weekly"):
        return False, "Only Daily and Weekly campaigns can be refreshed."

    # Never modify campaign content while an email is being sent.
    if campaign.status == "sending":
        return False, "Pause the campaign before refreshing its content."

    sending_count = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="sending"
    ).count()

    if sending_count:
        return False, "An email is currently being sent. Try again later."

    now = datetime.utcnow()

    if campaign.campaign_type == "daily":

        start_date = datetime(
            now.year,
            now.month,
            now.day
        )

        posts = (
            Post.query
            .filter(
                Post.is_published.is_(True),
                Post.published_at.isnot(None),
                Post.published_at >= start_date,
                Post.published_at <= now
            )
            .order_by(Post.published_at.desc())
            .limit(5)
            .all()
        )

        if not posts:
            return False, "No published news found for today."

        html_content = render_template(
            "emails/daily_news.html",
            posts=posts,
            subscriber=None,
            now=now
        )

    elif campaign.campaign_type == "weekly":

        seven_days_ago = now - timedelta(days=7)

        posts = (
            Post.query
            .filter(
                Post.is_published.is_(True),
                Post.published_at.isnot(None),
                Post.published_at >= seven_days_ago,
                Post.published_at <= now
            )
            .order_by(Post.published_at.desc())
            .limit(5)
            .all()
        )

        if not posts:
            return False, "No published news found within the last seven days."

        html_content = render_template(
            "emails/weekly_digest.html",
            posts=posts,
            subscriber=None,
            now=now
        )

    # Update only the campaign content.
    # Do not recreate recipients or reset their statuses.
    campaign.html_content = html_content

    if not safe_commit():
        return False, "Unable to save refreshed campaign content."

    return True, f"Campaign refreshed with {len(posts)} latest articles."

def delete_campaign(campaign_id):
    """
    Delete a campaign and its recipients.

    EmailLog records are intentionally preserved.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if not campaign:
        return False, "Campaign not found."

    if campaign.status == "sending":
        return False, "Pause the campaign before deleting it."

    sending_count = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="sending"
    ).count()

    if sending_count:
        return False, "An email is currently being sent."

    # Delete recipients first.
    CampaignRecipient.query.filter_by(
        campaign_id=campaign.id
    ).delete(synchronize_session=False)

    # Delete the campaign itself.
    db.session.delete(campaign)

    if not safe_commit():
        return False, "Unable to delete campaign."

    return True, "Campaign deleted successfully."

def create_user_campaign(
    name,
    subject,
    html_content,
    batch_size=20,
):
    """
    Create an email campaign for registered Superior News users.

    No emails are sent here. Recipients are queued for batch sending.
    """

    users = (
        User.query
        .filter(
            User._is_active.is_(True),
            User.is_deleted.is_(False),
            User.is_blocked.is_(False),
            User.email_verified.is_(True),
            User.email.isnot(None),
            User.email != "",
        )
        .order_by(User.id.asc())
        .all()
    )

    if not users:
        print("No eligible registered users found.")
        return None

    campaign = EmailCampaign(
        name=name,
        subject=subject,
        html_content=html_content,
        campaign_type="user_announcement",
        status="pending",
        batch_size=batch_size,
        total_recipients=len(users),
        sent_count=0,
        failed_count=0,
        completed_count=0,
        created_at=datetime.utcnow(),
    )

    db.session.add(campaign)
    db.session.flush()

    for index, user in enumerate(users):

        batch_number = (index // batch_size) + 1

        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            user_id=user.id,
            subscriber_id=None,
            email=user.email,
            batch_number=batch_number,
            status="pending",
        )

        db.session.add(recipient)

    total_batches = ceil(len(users) / batch_size)

    if not safe_commit():
        print("Failed to create registered-user campaign.")
        return None

    print(
        f"Registered-user campaign '{campaign.name}' created "
        f"({campaign.total_recipients} recipients, "
        f"{total_batches} batches)"
    )

    return campaign

def create_draft_campaign(draft_id):
    """
    Create an email campaign from a saved draft.
    """

    draft = DigestDraft.query.get_or_404(draft_id)

    # -------------------------
    # Single email
    # -------------------------
    if draft.audience == "single_email":

        subscriber = Subscriber.query.get(draft.subscriber_id)

        if not subscriber:
            return None

        html = render_template(
            "emails/admin_draft.html",
            subject=draft.subject,
            draft_html=draft.html_content,
            subscriber=subscriber,
            now=datetime.utcnow(),
        )

        result = send_email(
            to=subscriber.email,
            subject=draft.subject,
            html_content=html,
        )

        log_email(
            recipient=subscriber.email,
            subject=draft.subject,
            success=result["success"],
            subscriber=subscriber,
        )

        if result["success"]:
            draft.is_sent = True
            safe_commit()

        return None

    # -------------------------
    # Registered Superior News users
    # -------------------------
    if draft.audience == "registered_users":

        html = render_template(
            "emails/admin_draft.html",
            subject=draft.subject,
            draft_html=draft.html_content,
            subscriber=None,
            email_audience="registered_user",
            now=datetime.utcnow(),
        )

        campaign = create_user_campaign(
            name=draft.subject,
            subject=draft.subject,
            html_content=html,
            batch_size=20,
        )

        if campaign is None:
            return None

        draft.is_sent = True

        if not safe_commit():
            return None

        return campaign

    # -------------------------
    # Existing template selection
    # -------------------------
    if draft.audience == "tribe":
        template = "emails/tribe/admin_draft.html"
    else:
        template = "emails/admin_draft.html"

    html = render_template(
        template,
        subject=draft.subject,
        draft_html=draft.html_content,
        subscriber=None,
        now=datetime.utcnow(),
    )

    campaign = create_campaign(
        name=draft.subject,
        subject=draft.subject,
        html_content=html,
        campaign_type="draft",
    )

    if campaign is None:
        return None

    draft.is_sent = True
    safe_commit()

    return campaign

def send_next_batch(campaign_id):
    """
    Send the next pending batch of a campaign.

    Supports both registered users and newsletter subscribers.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if not campaign:
        return False
  
    # Protect older campaigns with NULL counters.
    campaign.sent_count = campaign.sent_count or 0
    campaign.failed_count = campaign.failed_count or 0
    campaign.completed_count = campaign.completed_count or 0
    campaign.total_recipients = campaign.total_recipients or 0

    if campaign.status in ("completed", "paused"):
        return False

    is_user_campaign = (
        campaign.campaign_type == "user_announcement"
    )

    campaign.status = "sending"

    recipients = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=campaign.id,
            status="pending",
        )
        .order_by(CampaignRecipient.id.asc())
        .limit(campaign.batch_size)
        .all()
    )

    if not recipients:

        pending = CampaignRecipient.query.filter_by(
            campaign_id=campaign.id,
            status="pending",
        ).count()

        if pending == 0:
            campaign.status = "completed"
            campaign.completed_at = datetime.utcnow()
            safe_commit()
            return True

    for recipient in recipients:

        # Resolve the correct recipient model.
        if is_user_campaign:
            account = User.query.get(recipient.user_id)
        else:
            account = Subscriber.query.get(
                recipient.subscriber_id
            )

        if not account:
            recipient.status = "failed"
            recipient.error = (
                "Registered user not found"
                if is_user_campaign
                else "Subscriber not found"
            )

            campaign.failed_count += 1
            campaign.completed_count += 1

            safe_commit()
            continue

        # Record sending attempt.
        recipient.status = "sending"
        recipient.sending_started_at = datetime.utcnow()
        recipient.attempts += 1
        recipient.last_attempt_at = datetime.utcnow()

        if not safe_commit():
            continue

        result = send_email(
            to=account.email,
            subject=campaign.subject,
            html_content=campaign.html_content,
        )

        # Temporary sending error.
        if not result["success"] and result["temporary"]:

            recipient.status = "paused"
            recipient.error = result["error"]

            campaign.status = "paused"
            campaign.paused_at = datetime.utcnow()

            safe_commit()
            return False

        if result["success"]:

            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            recipient.error = None

            campaign.sent_count += 1
            campaign.completed_count += 1

            # Only Subscriber has last_email_sent.
            if not is_user_campaign:
                account.last_email_sent = datetime.utcnow()

        else:

            recipient.status = "failed"
            recipient.error = result["error"]

            campaign.failed_count += 1
            campaign.completed_count += 1

        # Log both types of emails.
        log_email(
            recipient=account.email,
            subject=campaign.subject,
            success=result["success"],
            subscriber=None if is_user_campaign else account,
        )

        safe_commit()

    pending = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="pending",
    ).count()

    paused = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="paused",
    ).count()

    if pending == 0 and paused == 0:
        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        safe_commit()

    return True

def pause_campaign(campaign_id):
    """
    Pause an email campaign.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if campaign is None:
        return None

    if campaign.status == "completed":
        return campaign

    campaign.status = "paused"

    if not safe_commit():
        return None

    return campaign

def resume_campaign(campaign_id):
    """
    Resume a paused email campaign.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if campaign is None:
      return None
  
    CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="paused",
    ).update(
        {"status": "pending"},
        synchronize_session=False,
    )

    if campaign is None:
        return None

    if campaign.status == "completed":
        return campaign

    # Resume from where it stopped
    campaign.status = "pending"
    campaign.paused_at = None

    if not safe_commit():
        return None

    return campaign

def retry_failed_batch(campaign_id):
    """
    Retry all failed recipients in a campaign.

    Supports registered users and newsletter subscribers.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if campaign is None:
        return False
  
    campaign.sent_count = campaign.sent_count or 0
    campaign.failed_count = campaign.failed_count or 0
    campaign.completed_count = campaign.completed_count or 0
    campaign.total_recipients = campaign.total_recipients or 0

    is_user_campaign = (
        campaign.campaign_type == "user_announcement"
    )

    failed_recipients = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=campaign.id,
            status="failed",
        )
        .order_by(CampaignRecipient.batch_number.asc())
        .all()
    )

    if not failed_recipients:
        return True

    for recipient in failed_recipients:

        if is_user_campaign:
            account = User.query.get(recipient.user_id)
        else:
            account = Subscriber.query.get(
                recipient.subscriber_id
            )

        if not account:
            continue

        recipient.status = "sending"
        recipient.sending_started_at = datetime.utcnow()
        recipient.attempts += 1
        recipient.last_attempt_at = datetime.utcnow()

        if not safe_commit():
            continue

        result = send_email(
            to=account.email,
            subject=campaign.subject,
            html_content=campaign.html_content,
        )

        if not result["success"] and result["temporary"]:

            recipient.status = "paused"
            recipient.error = result["error"]

            campaign.status = "paused"
            campaign.paused_at = datetime.utcnow()

            safe_commit()
            return False

        if result["success"]:

            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            recipient.error = None

            campaign.sent_count += 1

            if campaign.failed_count > 0:
                campaign.failed_count -= 1

            campaign.completed_count += 1

            if not is_user_campaign:
                account.last_email_sent = datetime.utcnow()

        else:

            recipient.status = "failed"
            recipient.error = result["error"]

        log_email(
            recipient=account.email,
            subject=campaign.subject,
            success=result["success"],
            subscriber=None if is_user_campaign else account,
        )

        safe_commit()

    pending = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="pending",
    ).count()

    failed = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="failed",
    ).count()

    paused = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="paused",
    ).count()

    if pending == 0 and failed == 0 and paused == 0:
        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()

    safe_commit()

    return True

# ---------------------------
# Welcome email (new subscriber)
# ---------------------------
def send_welcome_email(subscriber_email, token):

    subscriber = Subscriber.query.filter_by(
        email=subscriber_email
    ).first()

    if not subscriber:
        return False

    html_content = render_template(
        "emails/welcome_email.html",
        subscriber=subscriber,
        now=datetime.utcnow()
    )

    result = send_email(
        subscriber_email,
        "Welcome to Superior News",
        html_content
    )

    if result["success"]:
        subscriber.last_email_sent = datetime.utcnow()

    log_email(
        subscriber_email,
        "Welcome to Superior News",
        result["success"],
        subscriber=subscriber
    )

    return result["success"]