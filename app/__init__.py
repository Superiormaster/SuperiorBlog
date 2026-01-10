from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.routes.public import public_bp
from app.routes.admin import admin_bp
from app.extensions import db, login_manager, cache, csrf
from markdown import markdown as md
from flask_migrate import Migrate
from app.models import AppSettings, Category, Post
import os

def create_app():
    app = Flask(__name__) 
    app.config.from_object(Config)

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

    app.config.update(
      CACHE_TYPE="SimpleCache",
      CACHE_DEFAULT_TIMEOUT=300
    )

    db.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)
    csrf.init_app(app)
    cache.init_app(app) 

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    # SAFE context processors (no crash)
    @app.context_processor
    def inject_globals():
        try:
            return {
                "nav_categories": Category.query.order_by(Category.name).all(),
                "breaking": Post.query.filter_by(
                    is_published=True
                ).order_by(Post.created_at.desc()).first()
            }
        except Exception:
            return {
                "nav_categories": [],
                "breaking": None
            }

    @app.context_processor
    def inject_settings():
        return dict(AppSettings=AppSettings)

    @app.template_filter('markdown')
    def markdown_filter(text):
        if not text:
            return ""
        return md(text, extensions=['fenced_code', 'codehilite', 'tables', 'nl2br'])

    return app