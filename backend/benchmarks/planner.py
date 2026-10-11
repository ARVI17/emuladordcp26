"""Synthetic, in-memory benchmark. Does not open any database or EA connection.

Run: python -m benchmarks.planner
"""
import json
import time
from app.models.entities import Player
from app.schemas.api import PlayerCreate
from app.services.squad_analysis import FORMATIONS, recommend_owned_squad


def measure(size):
    positions = ["POR", "LD", "DFC", "LI", "MCD", "MC", "MCO", "MD", "MI", "ED", "EI", "DC"]
    players = [Player(id=i+1, deleted=False, availability="available", **PlayerCreate(
        name=f"Synthetic {i}", athlete_id=f"athlete-{i}", position=positions[i % len(positions)],
        rating=60+i % 35, league="Test", club="Test", nationality="Test", price=None,
        attributes={key: 50+(i*7) % 45 for key in ("pace", "shooting", "passing", "dribbling", "defending", "physical")},
    ).model_dump()) for i in range(size)]
    started = time.perf_counter()
    results = [recommend_owned_squad(players, game_version="FC27", formation=f) for f in FORMATIONS]
    return {"synthetic_copies": size, "formations": len(results), "seconds": round(time.perf_counter()-started, 3),
            "statuses": [r["solver_status"] for r in results], "complete_lineups": sum(r["complete"] for r in results),
            "scope": "one balanced comparison across the formation catalog, in memory; excludes network and database"}


if __name__ == "__main__":
    for size in (132, 1000):
        print(json.dumps(measure(size)), flush=True)
