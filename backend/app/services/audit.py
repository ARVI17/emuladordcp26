from sqlalchemy.orm import Session
from app.models.entities import AuditLog

def record(db: Session, action: str, entity_type: str, entity_id: int | None = None, details: dict | None = None):
    db.add(AuditLog(action=action, entity_type=entity_type, entity_id=entity_id, details={**(details or {}), 'game_version': 'FC27'}))
