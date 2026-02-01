# admin_email.py
from app.models import Subscriber, Post, BreakingNews
from app.utils.email import send_bulk_email, send_weekly_digest
from datetime import datetime, timedelta

def send_welcome_email(email, token):
    unsubscribe_link = f"https://yourdomain.com/unsubscribe/{token}"
    html = f"""
    <h2>Welcome to Superior Blog!</h2>
    <p>Your ideas deserve an audience.</p>
    <p><a href='https://yourdomain.com/login'>Login & Start Creating</a></p>
    <p style='font-size:12px'>
        <a href='{unsubscribe_link}'>Unsubscribe</a>
    </p>
    """
    send_bulk_email(email, "Welcome to Superior Blog", html)

# ---------------------------
# Automatic Breaking News Digest
# ---------------------------
def send_latest_news():
    """Send breaking news from the last 24 hours to all active subscribers."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    news = BreakingNews.query.filter(BreakingNews.published_at >= yesterday).all()

    if not news:
        return  # nothing to send

    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()
    for s in subscribers:
        # build list items
        items = "".join([f"<li><a href='{n.url}'>{n.headline}</a></li>" for n in news])
        html = f"""
        <h2>Latest Breaking News</h2>
        <ul>{items}</ul>
        <p style='font-size:12px'>
            <a href='https://yourdomain.com/unsubscribe/{s.unsubscribe_token}'>Unsubscribe</a>
        </p>
        """
        send_bulk_email(s.email, "Breaking News Today", html)

#---------------------------
# Weekly Digest
# ---------------------------
def send_weekly_digest_to_all():
    """Send top 5 posts to all active subscribers."""
    subscribers = Subscriber.query.filter_by(is_active=True, receive_digest=True).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()

    for subscriber in subscribers:
        # `send_weekly_digest` should be your utility function that builds HTML + sends email
        send_weekly_digest(subscriber, posts)