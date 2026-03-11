from datetime import date
from flask import session
from app.models import DailyUsage
from app.extensions import db
from app.utils.db_helpers import safe_commit

LIMITS = {
    "guest": 3,
    "free": 5,
    "premium": None
}

def can_generate(user):
    today2 = str(date.today())

    # 1️⃣ Premium users → unlimited
    if user and getattr(user, "is_authenticated", False) and getattr(user, "is_premium", False):
        return True, None

    # 3️⃣ Logged-in free users → daily DB limit
    today = date.today()

    if user and getattr(user, "is_authenticated", False):
      usage = DailyUsage.query.filter_by(
          user_id=user.id,
          date=today
      ).first()
  
      if not usage:
          usage = DailyUsage(user_id=user.id, date=today, count=0)
          db.session.add(usage)
          safe_commit()
  
      if usage.count >= LIMITS["free"]:
          return False, usage
  
      usage.count += 1
      safe_commit()
  
      return True, usage

    anon_key = f"anon_usage_{today}"
    count = session.get(anon_key, 0)

    if count >= LIMITS["guest"]:
        return False, None

    session[anon_key] = count + 1
    return True, None