# Use python commands.py after deployment

from flask.cli import with_appcontext
from app.extensions import db
from app.models import Category
import click

@click.command("seed-categories")
@with_appcontext
def seed_categories():
    categories = [
        ("World", "world"),
        ("Sports", "sports"),
        ("Politics", "politics"),
        ("Business", "business"),
    ]

    for name, slug in categories:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))

    db.session.commit()
    click.echo("Categories seeded")