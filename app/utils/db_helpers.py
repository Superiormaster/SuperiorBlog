from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError

def safe_commit():
    try:
        db.session.commit()
        return True

    except SQLAlchemyError:
        current_app.logger.exception(
            "Database transaction failed."
        )

        db.session.rollback()
        return False