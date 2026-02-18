from app.models import User, Subscriber
from app.extensions import db

existing_users = User.query.all()
for user in existing_users:
    if not Subscriber.query.filter_by(email=user.email).first():
        db.session.add(Subscriber(email=user.email, user_id=user.id))
db.session.commit()