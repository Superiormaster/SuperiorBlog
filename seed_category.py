# seed_categories.py
from app import create_app
from app.extensions import db
from app.models import Category

app = create_app()

with app.app_context():
    categories = ["World", "Politics", "Business"]
    for name in categories:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, slug=name.lower()))
    db.session.commit()
    
# Use python seed_categories.py after deployment