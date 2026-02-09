from app import create_app
from app.extensions import db
from app.models import FootballCache
from app.utils.football import get_live_matches, get_league_table
from datetime import datetime

app = create_app()

with app.app_context():
    live = get_live_matches("PL")
    table = get_league_table("PL")

    print("LIVE:", len(live))
    print("TABLE:", table)

    # Live matches
    cache = FootballCache.query.filter_by(data_type="live", league="PL").first()
    if not cache:
        cache = FootballCache(data_type="live", league="PL")
        db.session.add(cache)

    cache.json_data = live
    cache.updated_at = datetime.utcnow()

    # League table
    cache = FootballCache.query.filter_by(data_type="table", league="PL").first()
    if not cache:
        cache = FootballCache(data_type="table", league="PL")
        db.session.add(cache)

    cache.json_data = table
    cache.updated_at = datetime.utcnow()

    db.session.commit()