from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user
from flask_mail import Mail
from flask import jsonify, url_for, redirect, flash
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
cache = Cache()
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()

@login_manager.unauthorized_handler
def unauthorized():
    flash("Please log in to continue.", "warning")
    return redirect(url_for("public.user_login"))

login_manager.login_view = "public.user_login" 