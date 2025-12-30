from app.extensions import db
from app.models import Label

labels = ["Breaking News", "Trending", "Editor's Pick"]

for name in labels:
    if not Label.query.filter_by(name=name).first():
        db.session.add(Label(name=name))

db.session.commit()