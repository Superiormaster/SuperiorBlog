from flask import Blueprint, render_template, request, jsonify
from app.utils.caption_generator import generate_caption, captions_today
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import desc
from app.moderation.sports import is_sports, sports_caption
from datetime import date
from app.extensions import db, csrf
from app.models import CaptionHistory
from app.utils.limits import can_generate
from app.utils.db_helpers import safe_commit

tools_bp = Blueprint('tool', __name__)

@tools_bp.route("/tools/football/stats")
def football_stats():
    return render_template("tools/football_stats.html")

@tools_bp.route("/tools/football/news")
def football_news():
    news = get_cached_football_news()
    return render_template("tools/football_news.html", news=news)