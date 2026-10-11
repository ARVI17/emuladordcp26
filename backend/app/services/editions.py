"""Edition boundaries: old cards stay in FC26; new work starts in FC27."""
import secrets
from sqlalchemy import select
from app.models.entities import AppSetting, Profile

DEFAULT_GAME_VERSION = "FC27"

def current_version(db) -> str:
    return db.scalar(select(Profile.game_version).order_by(Profile.id).limit(1)) or DEFAULT_GAME_VERSION

def ensure_profile(db) -> Profile:
    from app.services.contexts import ensure_local_context
    ensure_local_context(db)
    profile = db.scalar(select(Profile).order_by(Profile.id).limit(1))
    if profile is None:
        context = db.info.get("context")
        profile = Profile(name="Mi club", game_version=context.game_version if context and context.verified else DEFAULT_GAME_VERSION, coins=0, max_budget=0)
        db.add(profile)
    if db.get(AppSetting, "_import_signing_key") is None:
        db.add(AppSetting(key="_import_signing_key", value={"secret": secrets.token_urlsafe(32)}))
    db.flush()
    return profile
