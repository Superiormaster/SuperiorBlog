from datetime import date
from app.models import DailyUsage
from app.extensions import db

FREE_LIMIT = 5

def can_generate(user):
    if user.is_premium:
        return True, None

    today = date.today()
    usage = DailyUsage.query.filter_by(
        user_id=user.id, date=today
    ).first()

    if not usage:
        usage = DailyUsage(user_id=user.id, date=today, count=0)
        db.session.add(usage)

    if usage.count >= FREE_LIMIT:
        return False, usage
    return True, usage