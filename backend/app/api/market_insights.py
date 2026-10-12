from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import now
from app.models.planner import MarketAlert, MarketQuote
from app.schemas.api import InputModel
from app.services.audit import record
from app.services.contexts import utc
from app.services.editions import current_version
from app.services.locks import resource_locks

router = APIRouter(tags=['Observaciones de mercado'])
Market = Literal['Console', 'PC', 'Switch', 'Switch2']
Kind = Literal['listing', 'bid', 'observed_sale', 'allowed_range']


def quote_query(db, variant, market, kind):
    return select(MarketQuote).where(MarketQuote.game_version == current_version(db), MarketQuote.variant_id == variant, MarketQuote.market == market, MarketQuote.kind == kind).order_by(MarketQuote.observed_at.desc(), MarketQuote.id.desc())


def quote_data(row):
    return {'id': row.id, 'amount': row.amount, 'observed_at': row.observed_at, 'source_url': row.source_url,
            'coverage': row.coverage, 'expired': utc(row.expires_at) <= now() or now()-utc(row.observed_at) > timedelta(hours=24),
            'source': 'manual_review', 'verified_provider': False}


@router.get('/market/series')
def series(variant_id: str = Query(min_length=1, max_length=120), market: Market = 'Console', kind: Kind = 'listing', db: Session = Depends(get_db)):
    rows = list(db.scalars(quote_query(db, variant_id, market, kind).limit(201)))
    return {'game_version': current_version(db), 'variant_id': variant_id, 'market': market, 'kind': kind,
            'points': [quote_data(r) for r in reversed(rows[:200])], 'truncated': len(rows) > 200,
            'sales_volume': None, 'prediction': None, 'message': 'Hasta 200 observaciones manuales; sin interpolación, volumen ni predicción. Anuncios, pujas, ventas y rangos se consultan por separado.'}


class AlertInput(InputModel):
    variant_id: str = Field(min_length=1, max_length=120)
    market: Market
    kind: Kind = 'listing'
    direction: Literal['below', 'above']
    threshold: int = Field(ge=1, le=100_000_000)


class AlertToggle(InputModel):
    enabled: bool


def alert_data(db, row):
    quote = db.scalar(quote_query(db, row.variant_id, row.market, row.kind).limit(1))
    latest = quote_data(quote) if quote else None
    status = 'disabled' if not row.enabled else 'no_data' if not latest else 'stale' if latest['expired'] else 'triggered' if (quote.amount <= row.threshold if row.direction == 'below' else quote.amount >= row.threshold) else 'watching'
    return {k: getattr(row, k) for k in ('id', 'game_version', 'variant_id', 'market', 'kind', 'direction', 'threshold', 'enabled')} | {'status': status, 'latest': latest, 'remote_action': False}


@router.get('/market/alerts')
def alerts(offset: int = Query(default=0, ge=0, le=10000), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(MarketAlert).where(MarketAlert.game_version == current_version(db)).order_by(MarketAlert.enabled.desc(), MarketAlert.id.desc()).offset(offset).limit(51)))
    return {'items': [alert_data(db, r) for r in rows[:50]], 'has_more': len(rows) > 50, 'offset': offset}


@router.post('/market/alerts', status_code=201)
def add_alert(payload: AlertInput, db: Session = Depends(get_db)):
    from app.services.catalog_validation import require_variant
    require_variant(db, payload.variant_id)
    with resource_locks(db, 'market-alerts'):
        count = db.scalar(select(func.count()).select_from(MarketAlert).where(MarketAlert.game_version == current_version(db), MarketAlert.enabled.is_(True)))
        if count >= 50:
            raise HTTPException(409, 'Desactiva una alerta antes de superar 50 activas por edición')
        row = MarketAlert(**payload.model_dump(), game_version=current_version(db))
        db.add(row)
        db.flush()
        record(db, 'create_alert', 'market_alert', row.id)
        db.commit()
        return alert_data(db, row)


@router.patch('/market/alerts/{alert_id}')
def toggle_alert(alert_id: int, payload: AlertToggle, db: Session = Depends(get_db)):
    with resource_locks(db, 'market-alerts'):
        row = db.get(MarketAlert, alert_id)
        if not row or row.game_version != current_version(db):
            raise HTTPException(404, 'Alerta no disponible')
        if payload.enabled and not row.enabled:
            count = db.scalar(select(func.count()).select_from(MarketAlert).where(MarketAlert.game_version == current_version(db), MarketAlert.enabled.is_(True)))
            if count >= 50:
                raise HTTPException(409, 'Ya existen 50 alertas activas')
        row.enabled = payload.enabled
        record(db, 'toggle_alert', 'market_alert', row.id)
        db.commit()
        return alert_data(db, row)
