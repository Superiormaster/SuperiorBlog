from flask import Blueprint, render_template, request, jsonify, redirect
from flask_login import login_user, logout_user, current_user, login_required
import requests
from sqlalchemy import desc
from datetime import date
from app.extensions import db, csrf
from app.models import CaptionHistory
from app.utils.limits import can_generate
from app.utils.db_helpers import safe_commit
from app.utils.openai_service import generate_x_post_for_user
from app.forms import SubscribeForm

caption_bp = Blueprint('caption', __name__)

@caption_bp.route('/caption')
@login_required
def caption_page():
    form = SubscribeForm()
    editor_picks = CaptionHistory.query \
        .filter(CaptionHistory.style == "editor_pick") \
        .order_by(desc(CaptionHistory.confidence)) \
        .limit(5).all()
    return render_template('tools/caption.html', form=form, editor_picks=editor_picks)

@caption_bp.route("/captions/history")
@login_required
def caption_history_list():
    histories = CaptionHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(CaptionHistory.created_at.desc()).all()
    return render_template("tools/caption_history.html", histories=histories)

@caption_bp.route("/captions/history/<int:id>")
@login_required
def caption_history():
    items = CaptionHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(CaptionHistory.created_at.desc()).limit(20).all()

    return jsonify([
        {
            "id": item.id,
            "platform": item.platform,
            "created_at": item.created_at.strftime("%b %d, %Y %H:%M"),
            "preview": item.caption[:120]
        }
        for item in items
    ])

def use_token(user):
    if user.tokens > 0:
        user.tokens -= 1
        safe_commit()
        return True
    return False

@caption_bp.route('/caption/generate', methods=['POST'])
@csrf.exempt
@login_required
def generate_caption_route():
    try:

        # ---- Validate JSON ----
        if not request.is_json:
            return jsonify({"error": "Invalid JSON"}), 400

        data = request.get_json()
        text = data.get("text", "").strip()
        tone = data.get("tone")
        length = data.get("length", "short")
        platform = data.get("platform")
        intent = data.get("intent", "inform")
        mode = data.get("mode", "breaking")
        avoid_clickbait = data.get("avoid_clickbait", False)

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # ---- Daily Limit Check ----
        allowed, usage = can_generate(current_user)
        if not allowed:
            return jsonify({"error": "Daily limit reached"}), 403

        # ---- Token Check ----
        if current_user.tokens <= 0:
            return jsonify({
                "error": "premium_required",
                "redirect": url_for("public.pricing")
            }), 403

        # ---- Generate X Post Package ----
        results = generate_x_post_for_user(
            text=text,
            user=current_user,
            tone=tone,
            length=length,
            platforms=[platform] if platform else [],
            mode=mode,
            intent=intent,
            avoid_clickbait=avoid_clickbait
        )

        if not results:
            return jsonify({"error": "Caption generation failed."}), 500

        # ---- Deduct Token ONCE ----
        current_user.tokens -= 1
        safe_commit()

        # ---- Update Usage for Free Users ----
        if not current_user.is_premium and usage:
            usage.count += 1
            safe_commit()

        return jsonify(results)

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI request timed out."}), 504

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        return jsonify({"error": "Server error occurred."}), 500