"""Create the required local profile even when demonstration data is disabled."""
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.editions import ensure_profile


def bootstrap():
    if settings.seed_demo:
        from app.db.seed import seed_database
        seed_database()
    with SessionLocal() as db:
        ensure_profile(db)
        db.commit()

if __name__ == "__main__":
    bootstrap()
