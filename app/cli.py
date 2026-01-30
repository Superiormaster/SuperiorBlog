from .models import db, Category

def register_commands(app):
    @app.cli.command("seed_categories")
    def seed_categories():
        """Seed default categories into the database (safe for production)."""
        default_categories = [
            ("World", "world"),
            ("Politics", "politics"),
            ("Business", "business"),
            ("Sports", "sports"),
        ]

        for name, slug in default_categories:
            if not Category.query.filter_by(slug=slug).first():
                db.session.add(Category(name=name, slug=slug))
        db.session.commit()
        print("Categories seeded successfully!")