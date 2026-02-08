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
def log_email(recipient, subject, success):
    db.session.add(EmailLog(
        recipient=recipient,
        subject=subject,
        status="sent" if success else "failed"
    ))
    if not safe_commit():
        print("Failed to log email")


# ---------------------------
# Welcome email (new subscriber)
# ---------------------------
def send_welcome_email(subscriber_email, token):
    html_content = render_template(
        "emails/welcome_email.html",
        unsubscribe_token=token,
        now=datetime.utcnow()
    )

    success = send_email(subscriber_email, "Welcome to Superior News", html_content)
    log_email(subscriber_email, "Welcome to Superior News", success)


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

    for email in subscribers:
        log_email(email, "Daily News", success)


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

    for s in subscribers:
        html_content = render_template("emails/breaking_news.html", news_items=news_items,  subscriber=s, now=datetime.utcnow())
        success = send_email(to=s.email, subject="Breaking News Today", html_content=html_content)
        log_email(s.email, "Breaking News Today", success)


# ---------------------------
# Weekly Digest
# ---------------------------
def send_weekly_digest(subscriber, posts):
    """Send weekly digest to a single subscriber."""
    html_content = render_template(
        "emails/weekly_digest.html",
        posts=posts,
        subscriber=subscriber,
        now=datetime.utcnow()
    )

    success = send_email(subscriber.email, "Weekly Digest", html_content)
    log_email(subscriber.email, "Weekly Digest", success)


def send_weekly_digest_to_all():
    """Send top 5 posts to all active subscribers."""
    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()

    if not subscribers or not posts:
        return

    for subscriber in subscribers:
        send_weekly_digest(subscriber, posts)