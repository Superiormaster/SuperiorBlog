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
    """

    draft = DigestDraft.query.get_or_404(draft_id)

    # -------------------
    # Single email
    # -------------------
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

    # Select template
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
    
    draft.is_sent = True
    safe_commit()
    
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
            status="pending",
        )
        .order_by(CampaignRecipient.id.asc())
        .limit(campaign.batch_size)
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

    for recipient in recipients:

        subscriber = Subscriber.query.get(
            recipient.subscriber_id
        )

        if not subscriber:
            recipient.status = "failed"
            recipient.error = "Subscriber not found"
            campaign.failed_count += 1
            continue

        recipient.status = "sending"
        recipient.sending_started_at = datetime.utcnow()
        recipient.attempts += 1
        recipient.last_attempt_at = datetime.utcnow()
        
        if not safe_commit():
            continue

        html = campaign.html_content

        result = send_email(
            to=subscriber.email,
            subject=campaign.subject,
            html_content=html,
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
            campaign.completed_count += 1
        
        else:
        
            recipient.status = "failed"
            recipient.error = result["error"]
        
            campaign.failed_count += 1
            campaign.completed_count += 1
        
        log_email(
            recipient=subscriber.email,
            subject=campaign.subject,
            success=result["success"],
            subscriber=subscriber,
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

        recipient.status = "sending"
        recipient.sending_started_at = datetime.utcnow()
        
        recipient.attempts += 1
        recipient.last_attempt_at = datetime.utcnow()
    
        safe_commit()
    
        html = campaign.html_content

        result = send_email(
            to=subscriber.email,
            subject=campaign.subject,
            html_content=html,
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

        else:

            recipient.status = "failed"
            recipient.error = result["error"]

        log_email(
            recipient=subscriber.email,
            subject=campaign.subject,
            success=result["success"],
            subscriber=subscriber,
        )
  
        safe_commit()

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

    html_content = render_template(
        "emails/welcome_email.html",
        subscriber=subscriber,
        now=datetime.utcnow()
    )

    success = send_email(subscriber_email, "Welcome to Superior News", html_content)
    log_email(subscriber_email, "Welcome to Superior News", success, subscriber=subscriber)