"""Create the required local profile even when demonstration data is disabled."""
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.editions import ensure_profile


def bootstrap():
    with SessionLocal() as db:
        ensure_profile(db)
        from app.services.catalog_validation import load_documented_catalog
        load_documented_catalog(db)
        db.commit()

if __name__ == "__main__":
    bootstrap()
