from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.squad_analysis import analyze_club, formations_data

router = APIRouter(tags=["Análisis de club"])


class SquadRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formation: str = "4-3-3"
    style: Literal["balanced", "attacking", "defensive", "possession", "wide"] = "balanced"
    locked_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=11)
    excluded_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=5000)
    bench_size: int = Field(default=7, ge=0, le=12)
    include_loans: bool = True
    include_unreviewed: bool = False
    use_alternate_positions: bool = True
    avoid_main: bool = False

    @model_validator(mode="after")
    def consistent_ids(self):
        from app.services.squad_analysis import verified_formations
        if self.formation not in verified_formations():
            raise ValueError("Formación no disponible")
        for values in (self.locked_player_ids, self.excluded_player_ids):
            if len(values) != len(set(values)):
                raise ValueError("Los IDs no pueden repetirse")
        if set(self.locked_player_ids) & set(self.excluded_player_ids):
            raise ValueError("Una carta no puede estar fijada y excluida")
        return self


@router.get("/squads/formations")
def available_formations():
    return formations_data()


@router.get("/club/analysis")
def club_analysis(db: Annotated[Session, Depends(get_db)]):
    from app.services.contexts import require_module
    return {**analyze_club(db), "binding": require_module(db, "analysis")}


class ProfilesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disjoint: bool = False
    bench_size: int = Field(default=7, ge=0, le=12)
    locked_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=11)
    excluded_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=5000)
    include_loans: bool = True
    avoid_main: bool = False

    @model_validator(mode="after")
    def consistent_selection(self):
        for ids in (self.locked_player_ids, self.excluded_player_ids):
            if len(ids) != len(set(ids)):
                raise ValueError("No repitas copias en una selección")
        if set(self.locked_player_ids) & set(self.excluded_player_ids):
            raise ValueError("Una carta no puede estar fijada y excluida")
        if self.disjoint and self.locked_player_ids:
            raise ValueError("Los fijados comunes requieren alternativas; no pueden repetirse en equipos disjuntos")
        return self


@router.post("/club/profiles")
def squad_profiles(payload: ProfilesRequest, db: Annotated[Session, Depends(get_db)]):
    from sqlalchemy import select
    from app.models.entities import Player
    from app.services.contexts import require_module
    from app.services.editions import current_version
    from app.services.squad_analysis import verified_formations, recommend_owned_squad, effective_protected_ids
    binding = require_module(db, "squads")
    version = current_version(db)
    players = list(db.scalars(select(Player).where(Player.game_version == version, Player.deleted.is_(False))))
    protected = effective_protected_ids(db)
    profiles = [("Equilibrada", "balanced"), ("Protección defensiva", "defensive"), ("Ataque por bandas", "wide"), ("Combinaciones por dentro", "possession"), ("Sin gasto adicional", "balanced")]
    groups = []
    pending = []
    excluded = list(payload.excluded_player_ids)
    if payload.avoid_main:
        from app.services.main_squad import main_ids
        excluded = sorted(set(excluded) | main_ids(db))
    for name, style in profiles:
        choices = []
        for formation, slots in verified_formations().items():
            wide_slots = sum(position in {"MD", "MI", "ED", "EI"} for position in slots)
            if (style == "wide" and wide_slots < 2) or (style == "possession" and wide_slots):
                continue
            try:
                choices.append(recommend_owned_squad(players, game_version=version, formation=formation, style=style,
                    locked_player_ids=payload.locked_player_ids, excluded_player_ids=excluded,
                    include_loans=payload.include_loans, bench_size=payload.bench_size, protected_ids=protected))
            except ValueError:
                continue
        if not choices:
            pending.append({"profile": name, "reason": "No se pudo verificar una formación con estas copias fijadas/excluidas; revisa elegibilidad e identidad"})
            continue
        best = max(choices, key=lambda r: (len(r["lineup"]), sum(row["fit_score"] for row in r["lineup"])))
        signature = (best["formation"], tuple((r["slot"], r["player"]["id"]) for r in best["lineup"]), tuple(p['id'] for p in best['bench']))
        same = next((row for row in groups if row["signature"] == signature), None)
        if same:
            same["profiles"].append(name)
        else:
            groups.append({"profiles": [name], "signature": signature, "squad": best,
                           "tactic_status": "local_hypothesis", "why": "Mayor cobertura legal y encaje ponderado entre las formaciones evaluadas",
                           "additional_cost": 0, "chemistry_status": "unavailable",
                           "bench_missing": max(0, payload.bench_size-len(best["bench"])),
                           "data_quality": {"cards_with_attributes": sum(bool(p.get("attributes")) for p in best["players"]+best["bench"]), "cards": len(best["players"])+len(best["bench"])},
                           "practice": "Prueba un solo cambio y registra ocasiones, pérdidas y goles concedidos en tu diario.",
                           "vulnerability": "El cálculo no modela animaciones, habilidad del rival ni cansancio; contrasta el equilibrio en partido."})
        if payload.disjoint:
            excluded.extend(p["id"] for p in best["players"]+best["bench"])
    return {"binding": binding, "groups": [{k:v for k,v in g.items() if k != "signature"} for g in groups],
            "pending_profiles": pending, "mode": "disjoint_heuristic" if payload.disjoint else "alternatives", "simulation": True}


class JointRequest(BaseModel):
    segment_ids: list[int] = Field(min_length=1, max_length=6)
    player_ids: list[int] = Field(min_length=1, max_length=24)


@router.post("/dcp/joint-preview")
def joint_preview(payload: JointRequest, db: Annotated[Session, Depends(get_db)]):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.entities import Player, Segment
    from app.services.contexts import require_module
    from app.services.joint import joint_dcp
    from app.services.squad_analysis import effective_protected_ids
    from app.services.editions import current_version
    from app.api.routes import requirements_for_batch, score_progress
    binding = require_module(db, "dcp")
    segments = [db.get(Segment, identifier) for identifier in payload.segment_ids]
    if len(set(payload.segment_ids)) != len(segments) or any(not s or s.completed or s.challenge.game_version != current_version(db) for s in segments):
        raise HTTPException(409, "Hay segmentos repetidos o no disponibles")
    players = list(db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.game_version == current_version(db))))
    if len(players) != len(set(payload.player_ids)):
        raise HTTPException(409, "Hay copias no disponibles en esta edición")
    return {**joint_dcp(players, [{"id": s.id, "requirements": requirements_for_batch(db, s), "current_score": score_progress(db, s)} for s in segments], effective_protected_ids(db)), "binding": binding}


class TransferCandidate(BaseModel):
    card: dict
    quote_id: int


class TransferRequest(BaseModel):
    position: str
    budget: int = Field(ge=0, le=100_000_000)
    reserve: int = Field(default=0, ge=0, le=100_000_000)
    candidates: list[TransferCandidate] = Field(max_length=100)


@router.post("/transfers/compare")
def transfer_comparison(payload: TransferRequest, db: Annotated[Session, Depends(get_db)]):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.entities import Player
    from app.schemas.api import PlayerCreate, normalize_position
    from app.services.contexts import require_module
    from app.services.planner import valid_quote
    from app.services.squad_analysis import _fit, player_positions, serialize_player
    from app.services.editions import current_version
    binding = require_module(db, "transfers", allow_local=False)
    try:
        position = normalize_position(payload.position)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    available = min(payload.budget, db.info["context"].coins or 0)-payload.reserve
    owned = [p for p in db.scalars(select(Player).where(Player.deleted.is_(False), Player.game_version == current_version(db))) if p.availability == "available" and position in player_positions(p)]
    best = max(owned, key=lambda p: _fit(p, position)[0], default=None)
    choices = []
    for candidate in payload.candidates:
        try:
            fields = PlayerCreate.model_validate(candidate.card)
        except ValueError:
            raise HTTPException(422, "Ficha pública incompleta o inválida")
        if fields.game_version != current_version(db) or not fields.card_id or not fields.data_reviewed:
            raise HTTPException(409, "La variante pública no tiene edición e identidad revisadas")
        card = Player(**fields.model_dump())
        from app.services.catalog_validation import validate_copy
        if not validate_copy(db, card, explicit_edition='game_version' in fields.model_fields_set):
            raise HTTPException(409, 'La variante candidata no está documentada para FC27')
        if position not in player_positions(card):
            continue
        quote = valid_quote(db, candidate.quote_id, variant=card.card_id)
        if quote.amount > available:
            continue
        score, why = _fit(card, position)
        choices.append({"variant_id": card.card_id, "name": card.name, "price": quote.amount, "quote_id": quote.id,
                        "improvement": round(score-(_fit(best,position)[0] if best else 0),2), "why": why,
                        "market": quote.market, "observed_at": quote.observed_at, "source_url": quote.source_url,
                        "chemistry_status": "unavailable", "total_cost_status": "partial_unknown_complements"})
    choices.sort(key=lambda r:r["price"])
    tiers = {}
    for label,low,high in [("economica",0,.25),("intermedia",.25,.6),("ambiciosa",.6,1)]:
        rows = [r for r in choices if available*low <= r["price"] <= available*high]
        tiers[label] = max(rows,key=lambda r:r["improvement"],default=None)
    return {"binding":binding,"owned_alternative":serialize_player(best) if best else None,"tiers":tiers,
            "decision":"conservar_y_ahorrar" if not any(r["improvement"]>0 for r in choices) else "revisar_mejoras",
            "simulation":True,"missing":["Química oficial y costes complementarios antes de una recomendación económica cerrada"]}
