# admin_email.py
from app.utils.email import send_email
from app.models import Subscriber, Post, BreakingNews, EmailLog, User
from flask import render_template
from app.extensions import db
from app.utils.db_helpers import safe_commit
from datetime import datetime, timedelta

# ---------------------------
# Email logging helper
# ---------------------------
def log_email(recipient, subject, success, subscriber=None):
    db.session.add(EmailLog(
        subscriber_id=subscriber.id if subscriber else None,
        email=subscriber.email if subscriber else "unknown",
        subject=subject,
        status="sent" if success else "failed"
    ))
    if not safe_commit():
        print("Failed to log email")


# ---------------------------
# Welcome email (new subscriber)
# ---------------------------
def send_welcome_email(subscriber_email, token):

    subscriber = Subscriber.query.filter_by(email=subscriber_email).first()

    html_content = render_template(
        "emails/welcome_email.html",
        unsubscribe_token=token,
        now=datetime.utcnow()
    )

    success = send_email(subscriber_email, "Welcome to Superior News", html_content)
    log_email(subscriber_email, "Welcome to Superior News", success, subscriber=subscriber)


# ---------------------------
# Daily News
# ---------------------------
def send_daily_news():
    """Send daily news to all subscribed users"""
    subscribers = User.query.filter_by(is_subscribed=True).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()

    if not subscribers or not posts:
        return

    for subscriber in subscribers:
      if subscriber.last_email_sent and subscriber.last_email_sent.date() >= datetime.utcnow().date():
        continue  # Already sent today

      html_content = render_template(
          "emails/daily_news.html",
          posts=posts,
          subscriber=subscriber,
          now=datetime.utcnow()
      )

      success = send_email(
        to=subscriber.email,
        subject="📰 Superior Daily News",
        html_content=html_content
      )

    subscriber.last_email_sent = datetime.utcnow()
    db.session.add(subscriber)
    if not safe_commit():
      print(f"Failed to update last_email_sent for {subscriber.email}")

    log_email(subscriber.email, "Daily News", success, subscriber=subscriber)
    print(f"Daily News sent to {subscriber.email} at {subscriber.last_email_sent}")


# ---------------------------
# Breaking News
# ---------------------------
def send_latest_breaking_news():
    """Send breaking news from the last 24 hours to all active subscribers."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    news_items = Post.query.filter(
        Post.is_breaking == True,
        Post.is_published == True,
        Post.published_at >= yesterday
    ).order_by(Post.published_at.desc()).all()

    if not news_items:
        return  # Nothing to send

    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()

    for sub in subscribers:
        if sub.last_email_sent and sub.last_email_sent.date() >= datetime.utcnow().date():
            continue  # Already sent today

        html_content = render_template("emails/breaking_news.html", news_items=news_items,  subscriber=sub, now=datetime.utcnow())

        success = send_email(to=sub.email, subject="Breaking News Today", html_content=html_content)
        sub.last_email_sent = datetime.utcnow()
        db.session.add(sub)
        if not safe_commit():
            print(f"Failed to update last_email_sent for {sub.email}")

        log_email(sub.email, "Breaking News Today", success, subscriber=sub)
        print(f"Breaking News sent to {sub.email} at {sub.last_email_sent}")


# ---------------------------
# Weekly Digest
# ---------------------------
def send_weekly_digest(subscriber, posts):
    """Send weekly digest to a single subscriber."""

    if subscriber.last_email_sent and \
       subscriber.last_email_sent.date() >= datetime.utcnow().date():
        return

    html_content = render_template(
        "emails/weekly_digest.html",
        posts=posts,
        subscriber=subscriber,
        now=datetime.utcnow()
    )

    success = send_email(subscriber.email, "Weekly Digest", html_content)

    if success:
        subscriber.last_email_sent = datetime.utcnow()
        safe_commit()

    log_email(subscriber.email, "Weekly Digest", success, subscriber=subscriber)


def send_weekly_digest_to_all():
    """Send top 5 posts to all active subscribers."""
    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()

    if not subscribers or not posts:
        return

    for subscriber in subscribers:
        send_weekly_digest(subscriber, posts)