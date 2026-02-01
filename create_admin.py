from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

# Admin credentials
USERNAME = "Superior Master"
EMAIL = "ejeziepaschal@gmail.com"
PASSWORD = "Chidera@2006"

with app.app_context():
    # Try to find existing user by username or email
    user = User.query.filter(
        (User.username == USERNAME) | (User.email == EMAIL)
    ).first()

    if user:
        # Update password and ensure is_admin=True
        user.set_password(PASSWORD)
        user.is_admin = True
        user.role = "admin"
        db.session.commit()
        print("Admin password updated successfully.")
    else:
        # Create new admin user
        user = User(
            username=USERNAME,
            email=EMAIL,
            is_admin=True,
            role="admin"
        )
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
        print("Admin created successfully.")