# update_admin_password.py
from app import create_app
from app.extensions import db
from app.models import Admin
from werkzeug.security import generate_password_hash

app = create_app()

username = "Profnet1"
new_password = "Profnet@2005"  # your new password

with app.app_context():
    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        print(f"No admin with username '{username}' found.")
    else:
        admin.password = generate_password_hash(new_password)  # hash the new password
        db.session.commit()
        print(f"Password for admin '{username}' updated successfully.")