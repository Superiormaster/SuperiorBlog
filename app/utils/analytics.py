from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Post, User, Comment, Repost, PageView

def get_range(days):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end


now = datetime.utcnow()

def active_users(days=1):
    return db.session.query(
        func.count(func.distinct(User.id))
    ).filter(User.last_login >= now - timedelta(days=days)).scalar() or 0


def safe_list(value):
    return value if isinstance(value, list) else []


def track_login(user):
    user.login_count = (user.login_count or 0) + 1
    user.last_login = datetime.now(UTC)
    safe_commit()


def percentage_growth(current, previous):
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 2)


def active_users_by_day(days=7):
    results = db.session.query(
        func.date(User.last_login),
        func.count(func.distinct(User.id))
    ).filter(
        User.last_login >= now - timedelta(days=days)
    ).group_by(func.date(User.last_login)).all()

    labels = [str(r[0]) for r in results]
    values = [r[1] for r in results]
    return labels, values


def analytics_block(model, date_field, days):
    start, end = get_range(days)
    prev_start = start - timedelta(days=days)

    current = db.session.query(func.count()).filter(
        date_field.between(start, end)
    ).scalar() or 0

    previous = db.session.query(func.count()).filter(
        date_field.between(prev_start, start)
    ).scalar() or 0

    return current, percentage_growth(current, previous)