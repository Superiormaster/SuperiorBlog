# seed_label.py

from app import create_app
from app.extensions import db
from app.models import Label

labels = [
    "Breaking News",
    "Trending",
    "Politics",
    "Technology",
    "Sports",
    "Entertainment",
    "Business",
    "Editor's Pick"
]

app = create_app()

with app.app_context():
    for name in labels:
        if not Label.query.filter_by(name=name).first():
            db.session.add(Label(name=name))

    db.session.commit()
    print("✅ Labels seeded successfully")