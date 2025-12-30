# reset_admin.py
from app import create_app
from app.extensions import db
from app.models import Admin
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Delete old admin (if exists)
    admin = Admin.query.filter_by(username="Profnet1").first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
        print("Old admin deleted.")

    # Create new admin with hashed password
    new_admin = Admin(
        username="Profnet1",
        email="profnet100@gmail.com",
        password=generate_password_hash("Profnet@2005")
    )
    db.session.add(new_admin)
    db.session.commit()
    print("New admin created successfully!")