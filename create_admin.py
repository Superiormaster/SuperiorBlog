# create_admin.py
from app import create_app
from app.extensions import db
from app.models import Admin
from werkzeug.security import generate_password_hash

app = create_app()  # make sure your app factory is used

with app.app_context():
    admin = Admin(
        username="Profnet1",
        email="profnet100@gmail.com",
        password=generate_password_hash("Profnet@2005")
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin account created successfully!")