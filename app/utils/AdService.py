from datetime import datetime
from app.models import Ad

def get_active_ads(location):
    now = datetime.utcnow()

    ad = (
        Ad.query
        .filter_by(active=True, location=location)
        .filter(
            (Ad.start_date == None) | (Ad.start_date <= now),
            (Ad.end_date == None) | (Ad.end_date >= now)
        )
        .order_by(Ad.priority.desc())
        .first()
    )

    # Always return a list (empty if no ad)
    return [ad] if ad else []