from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
cache = Cache()
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()

login_manager.login_view = "admin.login" 