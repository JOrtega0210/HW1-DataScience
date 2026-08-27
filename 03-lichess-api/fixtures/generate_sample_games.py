"""One-off generator for fixtures/sample_games.ndjson.

The records are SYNTHETIC (not real Lichess games). They exist so `--demo` can
exercise the full Part A pipeline (DataFrame, stats, plots, CSV export)
without depending on live API access, in the same ndjson shape Lichess
returns from GET /api/games/user/{username}.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

USERNAME = "DemoPlayer"
OPENINGS = [
    ("B01", "Scandinavian Defense"),
    ("C50", "Italian Game"),
    ("B90", "Sicilian Defense: Najdorf Variation"),
    ("D02", "Queen's Pawn Game"),
    ("A45", "Indian Defense"),
    ("C60", "Ruy Lopez"),
    ("B10", "Caro-Kann Defense"),
    ("E60", "King's Indian Defense"),
]
OPPONENTS = ["RookRider", "KnightMare42", "PawnStorm", "SilentBishop", "QueenSac", "TowerDefense", "EnPassant99"]
SPEEDS = ["bullet", "blitz", "rapid"]

rows = []
rating = 1450
start = datetime(2026, 6, 1, tzinfo=timezone.utc)

for i in range(60):
    date = start + timedelta(hours=i * 9 + random.randint(0, 4))
    speed = random.choices(SPEEDS, weights=[0.3, 0.5, 0.2])[0]
    color = random.choice(["white", "black"])
    outcome_roll = random.random()
    if outcome_roll < 0.52:
        result = "win"
    elif outcome_roll < 0.90:
        result = "loss"
    else:
        result = "draw"

    rating_delta = {"win": random.randint(4, 12), "loss": -random.randint(4, 12), "draw": random.randint(-2, 2)}[result]
    rating += rating_delta
    opponent_rating = rating - rating_delta + random.randint(-60, 60)
    eco, opening_name = random.choice(OPENINGS)

    if result == "draw":
        winner = None
    else:
        winner = color if result == "win" else ("black" if color == "white" else "white")

    white = {"user": {"name": USERNAME if color == "white" else random.choice(OPPONENTS)}, "rating": rating if color == "white" else opponent_rating}
    black = {"user": {"name": USERNAME if color == "black" else random.choice(OPPONENTS)}, "rating": rating if color == "black" else opponent_rating}

    game = {
        "id": f"demo{i:04d}",
        "rated": True,
        "variant": "standard",
        "speed": speed,
        "createdAt": int(date.timestamp() * 1000),
        "status": "draw" if result == "draw" else "mate",
        "players": {"white": white, "black": black},
        "opening": {"eco": eco, "name": opening_name},
    }
    if winner:
        game["winner"] = winner

    rows.append(game)

out_path = Path(__file__).resolve().parent / "sample_games.ndjson"
with open(out_path, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

print(f"Wrote {len(rows)} synthetic games to {out_path}")
