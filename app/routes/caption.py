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

caption_bp = Blueprint('caption', __name__)

@caption_bp.route('/caption')
@login_required
def caption_page():
    editor_picks = CaptionHistory.query \
        .filter(CaptionHistory.style == "editor_pick") \
        .order_by(desc(CaptionHistory.confidence)) \
        .limit(5).all()
    return render_template('tools/caption.html', editor_picks=editor_picks)

@caption_bp.route("/captions/history")
@login_required
def caption_history_list():
    histories = CaptionHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(CaptionHistory.created_at.desc()).all()
    return render_template("tools/caption_history.html", histories=histories)

@caption_bp.route("/captions/history/<int:id>")
@login_required
def caption_history(id):
    history = CaptionHistory.query.filter_by(
        id=id,
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        "tools/caption_history_detail.html",
        history=history
    )

@caption_bp.route("/tools/x-generator")
@login_required
def x_generator():
    editor_picks = CaptionHistory.query \
        .filter_by(style="editor_pick") \
        .order_by(desc(CaptionHistory.confidence)) \
        .limit(5).all()

    return render_template("tools/x_generator.html", editor_picks=editor_picks)

@caption_bp.route('/caption/generate', methods=['POST'])
@csrf.exempt
@login_required
def generate_caption_route():
  try:
    allowed, usage = can_generate(current_user)
    if not allowed:
        return jsonify({"error": "Daily limit reached"}), 403

    # ---- Get JSON input ----
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    text = data.get("text", "").strip()
    tone = data.get("tone", None)
    length = data.get("length", "short")
    platforms = [data.get("platform", None)]
    intent = data.get("intent", "inform")
    mode = data.get("mode", "breaking")
    avoid_clickbait = data.get("avoid_clickbait", False)


    if not text:
      return jsonify({"error": "Text is required"}), 400

    # Ensure platforms is a list
    if isinstance(platforms, str):
      platforms = [platforms]
  
    # ---- Generate Captions ----
    results = generate_caption(
      text=text,
      user=current_user,
      tone=tone,
      length=length,
      platforms=platforms,
      mode=mode,
      intent=intent,
      avoid_clickbait=avoid_clickbait
      #platforms=["x"]
    )

    if not results:
      return jsonify({
        "error": "Caption generation failed. Please check network and try again."
      }), 500

    if not current_user.is_premium and usage:
      usage.count += 1
      if not safe_commit():
        print("Caption generated.")
    return jsonify({"results": results})
  except requests.exceptions.Timeout:
    flash("AI request timed out. Check your network.", "error")
    return {"caption": None, "error": "AI unavailable"}
  except Exception as e:
        print("❌ SERVER ERROR:", e)
        return jsonify({"error": "Server error occurred. Please try again."}), 500