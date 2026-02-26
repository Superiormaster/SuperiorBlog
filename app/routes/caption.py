from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
import requests
from sqlalchemy import desc
from datetime import date
from app.extensions import db, csrf
from app.models import CaptionHistory, XPost
from app.utils.limits import can_generate
from app.utils.db_helpers import safe_commit
from app.utils.openai_service import generate_x_post_for_user
from app.forms import SubscribeForm

caption_bp = Blueprint('caption', __name__)

ALLOWED_TONES = ["neutral", "breaking", "viral", "emotional", "professional"]
@caption_bp.route('/caption')
def caption_page():
    form = SubscribeForm()
    captions = None
    if current_user.is_authenticated:
        last_caption = XPost.query.filter_by(user_id=current_user.id)\
                                    .order_by(XPost.created_at.desc())\
                                    .first()
        if last_caption:
            captions = {
                "captions": [
                    {
                        "text": last_caption.text,
                        "confidence_score": last_caption.confidence_score,
                        "style": last_caption.style,
                        "suggested_replies": last_caption.suggested_replies or [],
                        "best_post_time": last_caption.best_post_time,
                        "image_url": last_caption.image_url
                    }
                ]
            }
    return render_template('tools/caption.html', form=form, captions=captions, allowed_tones=ALLOWED_TONES)

@caption_bp.route("/captions/history")
def caption_history_page():
    return render_template("tools/caption_history.html")

@caption_bp.route("/api/captions/history")
def caption_history_list():
    page = request.args.get("page", 1, type=int)

    pagination = CaptionHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        CaptionHistory.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    items = [
        {
            "id": item.id,
            "platform": item.platform,
            "created_at": item.created_at.strftime("%b %d, %Y %H:%M"),
            "preview": item.caption[:120]
        }
        for item in pagination.items
    ]

    return jsonify({
        "items": items,
        "has_next": pagination.has_next
    })

@caption_bp.route("/captions/history/item/<int:id>")
@login_required
def caption_history_item(id):
    item = CaptionHistory.query.filter_by(
        id=id,
        user_id=current_user.id
    ).first_or_404()

    return jsonify({
        "original_text": item.caption,
        "captions": [
            {
                "text": c.caption,
                "style": c.style,
                "confidence_score": c.confidence
            }
            for c in item.captions
        ]
    })

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
        MAX_INPUT_CHARS = 500
        MAX_OUTPUT_CHARS = 280

        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "Text is required"}), 400
        
        if len(text) > MAX_INPUT_CHARS:
            return jsonify({
                "error": f"Text exceeds max length of {MAX_INPUT_CHARS} characters."
            }), 400

        tone = data.get("tone")
        mode = data.get("mode", "single")
        premium_modes = ["thread", "engagement", "reply"]

        if mode in premium_modes and not current_user.is_premium:
            return jsonify({
                "error": "premium_required",
                "redirect": url_for("public.pricing")
            }), 403
        avoid_clickbait = data.get("avoid_clickbait", False)
        custom_prompt = data.get("custom_prompt")
        generate_image = data.get("generate_image")

        if generate_image and not current_user.is_premium:
            return jsonify({"error": "Image generation is premium only."}), 403

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
            mode=mode,
            avoid_clickbait=avoid_clickbait, 
            custom_prompt=custom_prompt,
            max_output_chars=MAX_OUTPUT_CHARS,
            generate_images=generate_image and current_user.is_premium
        )

        if not results:
            return jsonify({"error": "Caption generation failed."}), 500

        # ---- Deduct Token ONCE ----
        use_token(current_user)
        safe_commit()

        # ---- Update Usage for Free Users ----
        if not current_user.is_premium and usage:
            usage.count += 1
            safe_commit()

        return jsonify({
            **results,
            "tokens_remaining": current_user.tokens
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI request timed out."}), 504

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        return jsonify({"error": "Server error occurred."}), 500