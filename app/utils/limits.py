from datetime import date
from flask import session
from app.models import DailyUsage
from app.extensions import db
from app.utils.db_helpers import safe_commit

FREE_LIMIT = 30

def can_generate(user):
    # 1️⃣ Premium users → unlimited
    if user and user.is_authenticated and user.is_premium:
        return True, None

    # 3️⃣ Logged-in free users → daily DB limit
    today = date.today()

    usage = DailyUsage.query.filter_by(
        user_id=user.id,
        date=today
    ).first()

    if not usage:
        usage = DailyUsage(user_id=user.id, date=today, count=0)
        db.session.add(usage)
        safe_commit()

    if usage.count >= FREE_LIMIT:
        return False, usage

    usage.count += 1
    safe_commit()

    return True, usage