from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import AppSetting, Challenge, Objective, Player, Profile, Segment, Squad, SquadPlayer

FIRST = ["Álex", "Bruno", "Carlos", "Diego", "Enzo", "Fabián", "Gabriel", "Hugo", "Iker", "Julián", "Leo", "Mateo", "Nicolás", "Óscar", "Pablo"]
LAST = ["Acosta", "Bravo", "Cano", "Duarte", "Espina", "Flores", "Guerra", "Herrera", "Ibarra"]
POSITIONS = ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MC", "MCO", "ED", "DC", "EI"]
LEAGUES = ["Liga Aurora", "Premier Nova", "Serie Estelar", "Liga Central", "Liga Atlántica"]
CLUBS = ["Costa FC", "Unión Solar", "Real Norte", "Deportivo Sur", "Racing Verde", "Ciudad Azul", "Atlético Oro", "Sporting Luna", "Valle Rojo", "Puerto Blanco"]
NATIONS = ["Colombia", "España", "Argentina", "Brasil", "Francia", "México", "Uruguay", "Portugal"]

def seed_database() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Profile.id).limit(1)) is not None:
            return
        db.add(Profile(name="Club Local", coins=325000, platform="Consola", max_budget=125000, risk_level="medio", preferences={"rating_strategy": "floor_average"}))
        players = []
        for index in range(132):
            rating = 75 + ((index * 7) % 17)
            special = index % 23 == 0
            rare = special or index % 3 == 0
            role = "titular" if index < 11 else ("suplente" if index < 18 else ("reserva" if index < 23 else "club"))
            player = Player(
                name=f"{FIRST[index % len(FIRST)]} {LAST[(index * 2) % len(LAST)]} {index + 1}",
                rating=rating, position=POSITIONS[index % len(POSITIONS)], league=LEAGUES[index % len(LEAGUES)],
                club=CLUBS[index % len(CLUBS)], nationality=NATIONS[(index * 3) % len(NATIONS)],
                card_type="Especial Eclipse" if special else ("Oro raro" if rare else "Oro común"), rare=rare, special=special,
                tradable=index % 4 == 0, price=650 + (rating - 75) * 900 + (16000 if special else 0), chemistry=index % 4,
                protected=index < 11 or index in (27, 44), starter=index < 11, squad_role=role,
                usefulness=max(0, 92 - index) if index < 30 else index % 25, duplicate_untradeable=index in (25, 36, 47, 58, 69, 80, 91, 102),
            )
            db.add(player); players.append(player)
        db.flush()
        squad = Squad(name="Plantilla principal", formation="4-3-3", primary=True, protected=True)
        db.add(squad); db.flush()
        for index, player in enumerate(players[:11]): db.add(SquadPlayer(squad_id=squad.id, player_id=player.id, slot=f"{POSITIONS[index]}-{index + 1}"))
        challenges = [
            ("Mejora Oro", "Sobre de jugadores", [{"squad_size": 11, "min_rating": 78, "min_rare": 2}, {"squad_size": 11, "min_rating": 79, "min_chemistry": 8}]),
            ("Elección Estelar", "Elección 1 de 3", [{"squad_size": 11, "min_rating": 81, "min_rare": 4, "max_leagues": 5}]),
            ("Héroe Local", "Carta especial ficticia", [{"squad_size": 11, "min_rating": 80, "required_nation": "Colombia", "min_from_nation": 2}, {"squad_size": 11, "min_rating": 82, "min_chemistry": 10}]),
            ("Clásico de Clubes", "Sobre premium", [{"squad_size": 11, "min_rating": 77, "min_clubs": 4, "min_rare": 3}]),
            ("Especial Eclipse", "Carta Eclipse", [{"squad_size": 11, "min_rating": 83, "min_special": 1}, {"squad_size": 11, "min_rating": 84, "required_positions": {"DC": 1}}]),
        ]
        for name, reward, segments in challenges:
            challenge = Challenge(name=name, description=f"DCP demostrativo: {name}", reward=reward, expires_at=datetime.now(timezone.utc) + timedelta(days=14))
            db.add(challenge); db.flush()
            for number, req in enumerate(segments, 1): db.add(Segment(challenge_id=challenge.id, name=f"Segmento {number}", requirements=req))
        objective_names = ["Gana 3 partidos", "Marca 10 goles", "Asiste con centrocampistas", "Juega con Liga Aurora", "Mantén la portería", "Completa un DCP", "Compra cero jugadores", "Usa 5 nacionalidades"]
        for index, name in enumerate(objective_names):
            target = [3, 10, 5, 4, 2, 1, 5, 5][index]
            db.add(Objective(name=name, description="Objetivo demostrativo local", progress=index % 3, target=target, expires_at=datetime.now(timezone.utc) + timedelta(days=7 + index)))
        db.add(Objective(name="Evolución: Motor creativo", description="Evolución ficticia", category="Evolución", target=4, expires_at=datetime.now(timezone.utc) + timedelta(days=21)))
        db.add(Objective(name="Evolución: Muro defensivo", description="Evolución ficticia", category="Evolución", target=5, expires_at=datetime.now(timezone.utc) + timedelta(days=21)))
        db.add(AppSetting(key="optimizer", value={"tradable_penalty": 1500, "special_penalty": 50000, "duplicate_bonus": 8000, "rating_strategy": "floor_average"}))
        db.add(AppSetting(key="ollama", value={"model": "qwen2.5:3b"}))
        db.commit()
        print("Datos demostrativos creados: 132 jugadores, 5 DCP, 10 objetivos y 1 plantilla.")
    finally:
        db.close()

if __name__ == "__main__": seed_database()
