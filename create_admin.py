from app import create_app
from app.extensions import db
from app.models import Admin

app = create_app()

USERNAME = "Profnet1"
EMAIL = "profnet100@gmail.com"
PASSWORD = "Profnet@2005"

with app.app_context():
    admin = Admin.query.filter(
        (Admin.username == USERNAME) | (Admin.email == EMAIL)
    ).first()

    if admin:
        admin.set_password(PASSWORD)
        db.session.commit()
        print("Admin password updated successfully.")
    else:
        admin = Admin(username=USERNAME, email=EMAIL)
        admin.set_password(PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print("Admin created successfully.")