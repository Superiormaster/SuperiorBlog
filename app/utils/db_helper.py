from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError

def safe_commit():
    """
    Commit the current session. Rollback automatically on error.
    Returns True if successful, False otherwise.
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        print("Database error:", e)
        return False