from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Post, User, Comment, CaptionHistory, Repost

def get_range(days):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end


def percentage_growth(current, previous):
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 2)


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