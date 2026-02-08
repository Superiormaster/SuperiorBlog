from app import create_app
from app.utils.football import update_football_cache

app = create_app()
with app.app_context():
    print("Updating football cache...")
    update_football_cache()
    print("Done ✅")