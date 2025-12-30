# verify_admin.py
import os
from app import create_app
from app.extensions import db
from app.models import Admin

app = create_app()

with app.app_context():
    admins = Admin.query.all()
    if not admins:
        print("No admin accounts found.")
    else:
        for admin in admins:
            print(f"Username: {admin.username}, Email: {admin.email}")