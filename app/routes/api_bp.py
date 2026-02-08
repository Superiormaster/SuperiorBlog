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

api_bp = Blueprint('api', __name__)

@api_bp.route("/api/football/scores")
def football_scores():
    # Call Football-Data.org or API-SPORTS here
    return jsonify(matches=[...])