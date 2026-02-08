from app.utils.football import get_live_matches, get_league_table, get_upcoming_matches
from app.models import FootballCache
from app.extensions import db
from datetime import datetime

def update_football_cache():
    leagues = ["PL"]  # Add more if needed
    for league in leagues:
        # Live Matches
        live = get_live_matches(league)
        cache = FootballCache.query.filter_by(data_type="live", league=league).first()
        if not cache:
            cache = FootballCache(data_type="live", league=league)
            db.session.add(cache)
        cache.json_data = live
        cache.updated_at = datetime.utcnow()

        # League Table
        table = get_league_table(league)
        cache = FootballCache.query.filter_by(data_type="table", league=league).first()
        if not cache:
            cache = FootballCache(data_type="table", league=league)
            db.session.add(cache)
        cache.json_data = table
        cache.updated_at = datetime.utcnow()

    db.session.commit()