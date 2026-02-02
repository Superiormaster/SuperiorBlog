from flask import Flask, request, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.routes.public import public_bp
from app.routes.admin import admin_bp
from app.routes.caption import caption_bp
from app.routes.billing import billing_bp
from app.routes.comment import comments_bp
from app.extensions import db, login_manager, cache, csrf, mail
from flask_login import current_user
from flask_migrate import Migrate
from app.models import AppSettings, Category, Post
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.helper import publish_scheduled_posts
from .utils.scheduler import start_scheduler
import os
from datetime import datetime

def create_app():
    app = Flask(__name__) 
    app.config.from_object(Config)
  
    database_url = os.getenv("DATABASE_URL", "sqlite:///blog.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  
    app.config.update(
      CACHE_TYPE="SimpleCache",
      CACHE_DEFAULT_TIMEOUT=300
    )

    db.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)
    csrf.init_app(app)
    cache.init_app(app) 
    mail.init_app(app)
    start_scheduler(app)

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(caption_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(comments_bp)

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

    @app.context_processor
    def inject_year():
        return {'year': datetime.now().year}

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