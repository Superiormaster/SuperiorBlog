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
    batch_size=100,
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
        current_batch=1,
        total_recipients=len(subscribers),
        sent_count=0,
        failed_count=0,
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

    No emails are sent here.
    """

    posts = (
        Post.query
        .filter_by(is_published=True)
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
        now=datetime.utcnow()
    )

    campaign = create_campaign(
        name=f"Daily Digest {datetime.utcnow().strftime('%B %d, %Y')}",
        subject="📰 Superior Daily News",
        html_content=html_content,
        campaign_type="daily",
    )

    return campaign

def create_weekly_campaign():
    """
    Create a Weekly Digest campaign.

    No emails are sent here.
    """

    posts = (
        Post.query
        .filter_by(is_published=True)
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
        now=datetime.utcnow(),
    )

    campaign = create_campaign(
        name=f"Weekly Digest {datetime.utcnow().strftime('%B %d, %Y')}",
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

def create_draft_campaign(draft_id):
    """
    Create an email campaign from a saved draft.

    No emails are sent here.
    """

    draft = DigestDraft.query.get(draft_id)

    if not draft:
        return None

    html_content = render_template(
        "emails/admin_draft.html",
        subject=draft.subject,
        draft_html=draft.html_content,
        subscriber=None,
        now=datetime.utcnow(),
    )

    campaign = create_campaign(
        name=f"{draft.subject}",
        subject=draft.subject,
        html_content=html_content,
        campaign_type="draft",
    )

    return campaign

def send_next_batch(campaign_id):
    """
    Send the next pending batch of a campaign.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if not campaign:
        return False

    if campaign.status == "completed":
        return False

    if campaign.status == "paused":
        return False

    campaign.status = "sending"

    recipients = (
        CampaignRecipient.query
        .filter_by(
            campaign_id=campaign.id,
            batch_number=campaign.current_batch,
            status="pending",
        )
        .order_by(CampaignRecipient.id.asc())
        .all()
    )

    # Nothing left in this batch
    if not recipients:

        pending = CampaignRecipient.query.filter_by(
            campaign_id=campaign.id,
            status="pending",
        ).count()

        if pending == 0:
            campaign.status = "completed"
            safe_commit()
            return True

        campaign.current_batch += 1
        safe_commit()

        return send_next_batch(campaign.id)

    for recipient in recipients:

        subscriber = Subscriber.query.get(
            recipient.subscriber_id
        )

        if not subscriber:
            recipient.status = "failed"
            recipient.error = "Subscriber not found"
            campaign.failed_count += 1
            continue

        html = campaign.html_content

        success = send_email(
            to=subscriber.email,
            subject=campaign.subject,
            html_content=html,
        )
        time.sleep(0.2)

        if success:

            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()

            campaign.sent_count += 1

        else:

            recipient.status = "failed"
            recipient.error = "Email send failed"

            campaign.failed_count += 1

        log_email(
            recipient=subscriber.email,
            subject=campaign.subject,
            success=success,
            subscriber=subscriber,
        )

    # Is there another batch?

    pending = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="pending",
    ).count()

    if pending == 0:

        campaign.status = "completed"

    else:

        campaign.current_batch += 1

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

    if campaign.status == "completed":
        return campaign

    # Resume from where it stopped
    campaign.status = "pending"

    if not safe_commit():
        return None

    return campaign

def retry_failed_batch(campaign_id):
    """
    Retry all failed recipients in a campaign.
    """

    campaign = EmailCampaign.query.get(campaign_id)

    if campaign is None:
        return False

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

        subscriber = Subscriber.query.get(
            recipient.subscriber_id
        )

        if not subscriber:
            continue

        html = campaign.html_content

        success = send_email(
            to=subscriber.email,
            subject=campaign.subject,
            html_content=html,
        )

        if success:

            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            recipient.error = None

            campaign.sent_count += 1

            if campaign.failed_count > 0:
                campaign.failed_count -= 1

        else:

            recipient.error = "Retry failed"

        log_email(
            recipient=subscriber.email,
            subject=campaign.subject,
            success=success,
            subscriber=subscriber,
        )

    # Mark completed if nothing is left pending or failed
    pending = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="pending",
    ).count()

    failed = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="failed",
    ).count()

    if pending == 0 and failed == 0:
        campaign.status = "completed"

    safe_commit()

    return True

# ---------------------------
# Welcome email (new subscriber)
# ---------------------------
def send_welcome_email(subscriber_email, token):

    subscriber = Subscriber.query.filter_by(
        email=subscriber_email
    ).first()

    html_content = render_template(
        "emails/welcome_email.html",
        subscriber=subscriber,
        now=datetime.utcnow()
    )

    success = send_email(subscriber_email, "Welcome to Superior News", html_content)
    log_email(subscriber_email, "Welcome to Superior News", success, subscriber=subscriber)