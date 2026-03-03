from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
import requests, re, urllib.parse
from sqlalchemy import desc
from datetime import datetime
from app.extensions import db, csrf
from app.models import XPost, Post
from app.utils.limits import can_generate
from app.utils.db_helpers import safe_commit
from bs4 import BeautifulSoup
from app.forms import SubscribeForm
from app.utils.openai_service import generate_x_post_for_user

caption_bp = Blueprint('caption', __name__)

ALLOWED_TONES = ["neutral", "breaking", "viral", "emotional", "professional"]
@caption_bp.route('/landing')
def landing_page():
    """
    Landing page for the X Caption Engine.
    Shows countdown, sample caption (if available), and waitlist form.
    """
    # Fetch latest generated caption for demo (optional)
    latest_caption = None
    demo_posts = XPost.query.order_by(XPost.created_at.desc()).limit(1).all()
    if demo_posts:
        post = demo_posts[0]
        latest_caption = {
            "captions": [
                {
                    "text": post.text,
                    "style": post.style,
                    "confidence_score": post.confidence_score,
                    "best_post_time": post.best_post_time,
                    "image_url": post.image_url
                }
            ]
        }

    # Allowed tones (example)
    allowed_tones = ["funny", "serious", "informative", "casual"]

    return render_template(
        "tools/landing.html",
        captions=latest_caption,
        allowed_tones=allowed_tones
    )

@caption_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Handles waitlist subscriptions via email.
    """
    email = request.form.get("email")
    if not email:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("caption.landing_page"))

    # Check if already subscribed
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        flash("You are already on the waitlist! 🎉", "info")
        return redirect(url_for("caption.landing_page"))

    # Add subscriber
    new_sub = Subscriber(email=email)
    db.session.add(new_sub)
    safe_commit()

    flash("Thank you for joining the waitlist! 🚀", "success")
    return redirect(url_for("caption.landing_page"))

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
                        "confidence_score": last_caption.confidence_score,
                        "style": last_caption.style,
                        "suggested_replies": last_caption.suggested_replies or [],
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
    page = request.args.get("page", 1, type=int)

    pagination = XPost.query.filter_by(
        user_id=current_user.id
    ).order_by(
        XPost.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    items = [
        {
            "id": item.id,
            "platform": "X",
            "created_at": item.created_at.strftime("%b %d, %Y %H:%M"),
            "preview": item.text[:120]
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
    item = XPost.query.filter_by(
        id=id,
        user_id=current_user.id
    ).first_or_404()

    return jsonify({
        "original_text": item.text,
        "captions": [
            {
                "text": caption.text,
                "style": caption.style,
                "confidence_score": caption.confidence
            }
            for caption in item.suggested_replies or []
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
def generate_caption_route():
    if not current_user.is_authenticated:
        flash("You need to be logged in to generate captions.", "error")
        return redirect(url_for('public.user_login'))

    try:
        # ---- Validate JSON ----
        if not request.is_json:
            flash("Invalid JSON format. Please check your input and try again.", "error")
            return redirect(url_for('caption.caption_page'))

        data = request.get_json()
        MAX_INPUT_CHARS = 500
        MAX_OUTPUT_CHARS = 280

        text = data.get("text", "").strip()
        if not text:
            flash("Text is required.", "error")
            return redirect(url_for('caption.caption_page'))
        
        if len(text) > MAX_INPUT_CHARS:
            flash(f"Text exceeds max length of {MAX_INPUT_CHARS} characters.", "error")
            return redirect(url_for('caption.caption_page'))

        tone = data.get("tone")
        mode = data.get("mode", "single")
        premium_modes = ["thread", "engagement", "reply"]

        if mode in premium_modes and not current_user.is_premium:
            flash("Premium access required for this mode. Please upgrade.", "error")
            return redirect(url_for("public.pricing"))

        avoid_clickbait = data.get("avoid_clickbait", False)
        custom_prompt = data.get("custom_prompt")
        generate_image = data.get("generate_image")

        # ---- Daily Limit Check ----
        allowed, usage = can_generate(current_user)

        print(f"User: {current_user}, Allowed: {allowed}, Usage: {usage}")

        if not allowed:
          flash("You've reached your daily limit. Please try again tomorrow or upgrade to premium.", "error")
          return redirect(url_for("caption.caption_page"))

        # ---- Token Check ----
        if not current_user.is_premium and current_user.tokens <= 0:
            flash("You need more tokens. Please upgrade to premium for unlimited access.", "error")
            return redirect(url_for("public.pricing"))

        # ---- Generate X Post Package ----
        results = generate_x_post_for_user(
            text=text,
            user=current_user,
            tone=tone,
            mode=mode,
            avoid_clickbait=avoid_clickbait, 
            custom_prompt=custom_prompt,
            max_output_chars=MAX_OUTPUT_CHARS
        )

        if not results:
            flash("Caption generation failed. Please try again.", "error")
            return redirect(url_for('caption.caption_page'))

        # ---- Deduct Token ONCE ----
        use_token(current_user)

        # ---- Update Usage for Free Users ----
        if not current_user.is_premium and usage:
            usage.count += 1
            safe_commit()

        return jsonify({
            **results,
            "tokens_remaining": current_user.tokens
        })

    except requests.exceptions.Timeout:
        flash("AI request timed out. Please try again.", "error")
        return redirect(url_for('caption.caption_page'))

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        flash("A server error occurred. Please try again later.", "error")
        return redirect(url_for('caption.caption_page'))