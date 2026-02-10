# upgrade.py
from app import create_app
from flask_migrate import upgrade
from app.extensions import db
from app.models import Category, Label, User

app = create_app()

# Admin credentials
ADMIN_USERNAME = "Superior Master"
ADMIN_EMAIL = "ejeziepaschal@gmail.com"
ADMIN_PASSWORD = "Chidera@2006"

# Default categories
categories = [
    ("World", "world"),
    ("Politics", "politics"),
    ("Business", "business"),
    ("Sports", "sports"),
    ("Education", "education"),
    ("Lifestyle", "lifestyle"),
    ("Nigeria", "nigeria"),
    ("Technology", "technology"),
    ("Health", "health"),
    ("Entertainment", "entertainment"),
    ("Personal Finance", "personal-finance"),
]

# Default labels
labels = [
    "Breaking News",
    "Trending",
    "Politics",
    "Technology",
    "Sports",
    "Entertainment",
    "Business"
]

with app.app_context():
    # 1️⃣ Run migration
    upgrade()
    print("✅ Database migrated successfully")

    # 2️⃣ Seed categories
    for name, slug in categories:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))
    db.session.commit()
    print("✅ Categories seeded successfully")
    """try:
    if not Category.query.first():
        # seed logic
except Exception as e:
    print("Skipping category seed:", e)"""

    # 3️⃣ Seed labels
    for name in labels:
        if not Label.query.filter_by(name=name).first():
            db.session.add(Label(name=name))
    db.session.commit()
    print("✅ Labels seeded successfully")

    # 4️⃣ Create or update admin user
    user = User.query.filter(
        (User.username == ADMIN_USERNAME) | (User.email == ADMIN_EMAIL)
    ).first()

    if user:
        user.set_password(ADMIN_PASSWORD)
        user.is_admin = True
        user.role = "admin"
        print("✅ Admin password updated successfully")
    else:
        user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            is_admin=True,
            role="admin"
        )
        user.set_password(ADMIN_PASSWORD)
        db.session.add(user)
        print("✅ Admin created successfully")

    db.session.commit()