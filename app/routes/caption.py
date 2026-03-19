from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
import requests, re, urllib.parse, pytz
from sqlalchemy import desc
from datetime import datetime, timedelta
from app.extensions import db, csrf
from app.models import XPost, Post
from app.utils.limits import can_generate
from app.utils.db_helpers import safe_commit
from app.utils.limits import LIMITS
from sqlalchemy import or_
from bs4 import BeautifulSoup
from app.forms import SubscribeForm
from app.utils.openai_service import generate_x_post_for_user

caption_bp = Blueprint('caption', __name__)

local_tz = pytz.timezone("Africa/Lagos")
ALLOWED_TONES = ["neutral", "breaking", "viral", "emotional", "professional"]
@caption_bp.route('/landing')
def landing_page():
    """
    Landing page for the X Caption Engine.
    """

    return render_template(
        "tools/landing.html"
    )

@caption_bp.route('/caption')
def caption_page():
    form = SubscribeForm()
    captions = None
    snippet = request.args.get("snippet", "")

    if snippet:
        snippet = urllib.parse.unquote(snippet)

    if current_user.is_authenticated:
        last_caption = XPost.query.filter_by(user_id=current_user.id)\
                                    .order_by(XPost.created_at.desc())\
                                    .first()
        if last_caption:
            captions = {
                "captions": [
                    {
                        "text": last_caption.text,
                        "style": last_caption.style,
                    }
                ]
            }
    return render_template('tools/caption.html', form=form, captions=captions, datetime=datetime, allowed_tones=ALLOWED_TONES, snippet=snippet)

@caption_bp.route('/generate-thread/<int:post_id>')
def generate_thread_from_post(post_id):

    post = Post.query.get_or_404(post_id)

    soup = BeautifulSoup(post.content, "html.parser")
    clean_text = soup.get_text()

    # Collect first 500 characters
    content_snippet = re.sub(r'\s+', ' ', clean_text).strip()[:500]

    if not content_snippet.strip():
        return "Post has no content", 400

    return redirect(
        url_for(
            'caption.caption_page',
            snippet=urllib.parse.quote(content_snippet)
        )
    )

@caption_bp.route("/captions/history")
@login_required
def caption_history_page():
    return render_template("tools/caption_history.html")

@caption_bp.route("/api/captions/history")
@login_required
def caption_history_list():
    try:
      page = request.args.get("page", 1, type=int)
      start_date_str = request.args.get("start_date")
      end_date_str = request.args.get("end_date")
  
      query = XPost.query.filter_by(user_id=current_user.id)
  
      if start_date_str:
          start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
          query = query.filter(XPost.created_at >= start_date)
  
      if end_date_str:
          end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
          query = query.filter(XPost.created_at < end_date)
  
      pagination = query.order_by(XPost.created_at.desc()).paginate(
          page=page, per_page=20, error_out=False
      )
  
      nigeria_tz = pytz.timezone("Africa/Lagos")

      items = []
      for item in pagination.items:
            captions = getattr(item, "captions", []) or []
            preview_text = captions[0]["text"] if captions else item.text

            created_local = item.created_at.replace(tzinfo=pytz.utc).astimezone(nigeria_tz)
            created_str = created_local.strftime("%b %d, %Y %H:%M")

            items.append({
                "id": item.id,
                "platform": "X",
                "created_at": created_str,
                "preview": preview_text[:120]
            })

      return jsonify({
          "items": items,
          "has_next": pagination.has_next
      })
    except Exception as e:
        return jsonify({"error": str(e), "items": [], "has_next": False})

@caption_bp.route("/captions/history/item/<int:id>")
@login_required
def caption_history_item(id):
    try:
        item = XPost.query.filter_by(id=id, user_id=current_user.id).first_or_404()

        captions_json = getattr(item, "captions", []) or []

        captions_list = []
        for cap in captions_json:
            captions_list.append({
                "text": cap.get("text", ""),
                "style": cap.get("style", item.style),
                "suggested_replies": cap.get("suggested_replies", []) or [],
                "thread": cap.get("thread", []) or item.threads or []
            })

        if not captions_list and item.text:
            captions_list.append({
                "text": item.text,
                "style": item.style,
                "suggested_replies": item.suggested_replies or [],
                "thread": item.threads or []
            })

        return jsonify({
            "original_text": item.original_text or item.text,
            "captions": captions_list
        })
    except Exception as e:
        return jsonify({
            "error": "failed_to_load",
            "message": str(e),
            "original_text": "",
            "captions": []
        }), 500

@caption_bp.route("/caption/guidelines")
@login_required
def caption_guidelines():
    return render_template("tools/caption_guidelines.html")

def use_token(user):
    if not user:
        return False

    if getattr(user, "is_premium", False):
        return True

    if getattr(user, "tokens", 0) > 0:
        user.tokens -= 1
        safe_commit()
        return True
    return False

def check_user_tokens(user):
    if not user:
        return {"allowed": True}

    if getattr(user, "is_premium", False):
        return {"allowed": True}

    if getattr(user, "tokens", 0) > 0:
        return {"allowed": True}

    return {
        "allowed": False,
        "error": "tokens_exhausted",
        "message": "You have no more tokens. Please upgrade to premium to continue."
    }

@caption_bp.route('/caption/generate', methods=['POST'])
@csrf.exempt
def generate_caption_route():
    try:
        # ---- Validate JSON ----
        if not request.is_json:
            return jsonify({
                "error": "invalid_request",
                "message": "Invalid JSON format."
            }), 400

        data = request.get_json()
        MAX_INPUT_CHARS = 500
        MAX_OUTPUT_CHARS = 280

        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "Text is required."}), 400
        
        if len(text) > MAX_INPUT_CHARS:
            return jsonify({
                "error": f"Text exceeds {MAX_INPUT_CHARS} characters."
            }), 400

        user = current_user if getattr(current_user, "is_authenticated", False) else None

        tone = data.get("tone")
        mode = data.get("mode", "single")
        platform = data.get("platform", "x")
        premium_modes = ["thread", "engagement", "reply", "ultra_viral", "3_captions"]

        if mode in premium_modes and (not user or not getattr(user, "is_premium", False)):
            return jsonify({
                "error": "premium_required",
                "message": "Premium required for this mode.",
                "redirect": url_for("public.pricing")
            }), 403

        avoid_clickbait = data.get("avoid_clickbait", False)
        custom_prompt = data.get("custom_prompt")

        # ---- Daily Limit Check ----
        allowed, usage = can_generate(user)

        if not allowed:
            msg = "Daily limit reached. Log in to get more captions." if not user else "Daily limit reached. Upgrade to continue."
            return jsonify({"error": "daily_limit_reached", "message": msg}), 403

        if user and not getattr(user, "is_premium", False):
          token_status = check_user_tokens(user)
          if not token_status["allowed"]:
              return jsonify(token_status), 403

        # ---- Generate X Post Package ----
        results = generate_x_post_for_user(
            text=text,
            user=user,
            tone=tone,
            mode=mode,
            platform=platform,
            avoid_clickbait=avoid_clickbait, 
            custom_prompt=custom_prompt,
        )

        if not results or not results.get("captions"):
            return jsonify({
                "error": "generation_failed",
                "message": "Caption generation failed."
            }), 500

        if user and getattr(user, "is_authenticated", False) and not getattr(user, "is_premium", False):
          use_token(user)

        # ---- Update Usage for Free Users ----
        if user and not getattr(user, "is_premium", False) and usage:
            usage.count += 1
            safe_commit()

        warning_msg = None
        if user and not getattr(user, "is_premium", False):
            remaining = LIMITS["free"] - usage.count if usage else None
            if remaining is not None and remaining <= 3:
              warning_msg = f"⚠️ Only {user.tokens} tokens remaining."

        return jsonify({
            **results,
            "tokens_remaining": getattr(user, "tokens", None),
            "warning": warning_msg
        })

    except requests.exceptions.Timeout:
        return jsonify({
          "error": "server timeout",
          "message": "AI request timeout. Please try again."
        }), 504

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        return jsonify({
          "error": "server failed",
          "message": "Server error occurred. Please try again later."
        }), 500