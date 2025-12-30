# create_admin.py
from app import create_app
from app.extensions import db
from app.models import Admin
from werkzeug.security import generate_password_hash

# Admin credentials
username = "Profnet1"
email = "profnet100@gmail.com"
password = "Profnet@2005"  # <-- plaintext password, will be hashed

app = create_app()

with app.app_context():
    # Check if admin already exists
    existing = Admin.query.filter_by(username=username).first()
    if existing:
        print(f"⚠️ Admin '{username}' already exists. No changes made.")
    else:
        # Create new admin with hashed password
        hashed_password = generate_password_hash(password, method="scrypt")
        admin = Admin(username=username, email=email, password=hashed_password)
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Admin '{username}' created successfully!")