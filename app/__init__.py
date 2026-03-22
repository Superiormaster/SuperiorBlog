from flask import Flask, request, url_for, redirect, session, flash, has_request_context
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.routes.public import public_bp
from app.routes.admin import admin_bp
from app.routes.caption import caption_bp
from app.routes.billing import billing_bp
from app.routes.ads import ads_bp
from uuid import uuid4
from app.extensions import db, login_manager, cache, csrf, mail
from flask_login import current_user
from flask_migrate import Migrate
from app.models import AppSettings, Category, Post, PageView, User
from app.forms import UserLoginForm
import os, pytz
from app.utils.db_helpers import safe_commit
from app.utils.AdService import get_active_ads
from datetime import datetime, UTC, date

migrate = Migrate()

def create_app():
    app = Flask(__name__,
    template_folder="templates" ) 
    app.config.from_object(Config)
  
    database_url = os.getenv("DATABASE_URL", "sqlite:///blog.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
  
    app.config.update(
      CACHE_TYPE="SimpleCache",
      CACHE_DEFAULT_TIMEOUT=300
    )

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    cache.init_app(app) 
    mail.init_app(app)

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(caption_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(ads_bp)

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id or user_id == "None":
            return None
        return User.query.get(int(user_id))

    # Unauthorized handler
    @login_manager.unauthorized_handler
    def unauthorized():
        flash("Please log in to continue.", "warning")
        return redirect(url_for("public.user_login"))

    # SAFE context processors (no crash)
    @app.context_processor
    def inject_globals():
        nav_categories = []
        breaking_post = None
        try:
            nav_categories = Category.query.order_by(Category.name).all()
            breaking_post = Post.query.filter_by(
                is_published=True
            ).order_by(Post.created_at.desc()).first()
        except Exception:
            pass  # Will return empty list / None if tables not ready

        return {
            "nav_categories": nav_categories,
            "breaking": breaking_post
        }

    @app.before_request
    def redirect_root_to_www():
        if request.host == "superiornews.app":
            return redirect("https://www.superiornews.app" + request.full_path, code=301)

    @app.context_processor
    def inject_year():
        return {'year': datetime.now().year}

    @app.template_filter("localtime")
    def localtime_filter(utc_dt):
        if not utc_dt:
            return ""
    
        nigeria = pytz.timezone("Africa/Lagos")
        return utc_dt.replace(tzinfo=pytz.utc).astimezone(nigeria)

    @app.template_filter("datetimeformat")
    def datetimeformat(value, format="%B %d, %Y %I:%M %p"):
      if value is None:
        return ""
      return value.strftime(format)

    @app.before_request
    def update_last_seen():
        if current_user.is_authenticated:
            current_user.last_seen = datetime.now(UTC)
            safe_commit()
    
    @app.context_processor
    def inject_ads():
        return dict(get_active_ads=get_active_ads)
    
    @app.before_request
    def track_page_view():
        if request.endpoint in ("static",):
            return
    
        session_id = session.get("sid")
        if not session_id:
            session["sid"] = session_id = str(uuid4())
    
        view = PageView(
            user_id=current_user.id if current_user.is_authenticated else None,
            session_id=session_id,
            path=request.path,
            ip_address=request.remote_addr
        )
        db.session.add(view)
        safe_commit()

    @app.before_request
    def reset_daily_tokens():
        if current_user.is_authenticated:
            today = date.today()
            if current_user.last_token_reset != today:
                current_user.tokens = 5
                current_user.last_token_reset = today
                safe_commit()

    @app.context_processor
    def inject_login_form():
      if not has_request_context():
        return {}
      return dict(login_form=UserLoginForm())
    
    @app.before_request
    def require_profile_completion():
    # Not logged in? No restriction.
      if not current_user.is_authenticated:
        return
    
      # Profile already completed? No restriction.
      if current_user.profile_completed:
        return
    
      # Safety: request.endpoint can be None
      if request.endpoint is None:
        return
    
      allowed_endpoints = {
        "public.profile_setup",
        "public.logout",
        "public.user_login",
        "public.google_one_tap",
        "public.google_callback",
        "public.google_login",
        "public.upload_image_route"
      }
    
      if request.endpoint in allowed_endpoints:
        return
    
      # Allow static files
      if request.endpoint.startswith("static"):
        return
    
      # Allow auth & admin blueprints entirely
      if request.blueprint == "admin":
        return
    
      # Otherwise force profile setup
      return redirect(url_for("public.profile_setup"))
    
    @app.context_processor
    def inject_settings():
      return dict(AppSettings=AppSettings)
    
    return app