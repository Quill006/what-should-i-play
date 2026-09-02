"""
Storage.

The whole catalogue is a single SQLite file — no server to install, and it
travels with the project. A few thousand games is small enough that we load
all of them into memory once at startup and score them in plain Python.

That sounds wasteful and isn't: 5,000 dictionaries is a few megabytes, and
scoring them takes about a millisecond. Trying to express the scoring formula
in SQL would make it far harder to read and change, which is the opposite of
what this project needs.
"""

import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "games.db"
SEED_PATH = PROJECT_ROOT / "scripts" / "seed_data.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY,
    slug          TEXT,
    name          TEXT NOT NULL,
    released      TEXT,
    year          INTEGER,
    metacritic    INTEGER,
    playtime      INTEGER,
    rating        REAL,
    ratings_count INTEGER,
    image         TEXT,
    url           TEXT,
    platforms     TEXT NOT NULL,  -- JSON array
    genres        TEXT NOT NULL,  -- JSON array
    tags          TEXT NOT NULL   -- JSON array
);
"""

# SQLite has no array type. Storing these three fields as JSON strings keeps
# the schema simple; we decode them on the way out. If you ever need to query
# by tag in SQL, that's the point to switch to a proper join table.
JSON_COLUMNS = ("platforms", "genres", "tags")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row  # rows behave like dicts
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


def save_games(games: list[dict]) -> int:
    """
    Insert or update games. Re-running the fetch script refreshes existing
    rows rather than duplicating them, because id is the primary key.
    """
    init_db()
    rows = [
        (
            game["id"],
            game.get("slug"),
            game["name"],
            game.get("released"),
            int(game["released"][:4]) if game.get("released") else None,
            game.get("metacritic"),
            game.get("playtime"),
            game.get("rating"),
            game.get("ratings_count"),
            game.get("image"),
            game.get("url"),
            json.dumps(game.get("platforms", [])),
            json.dumps(game.get("genres", [])),
            json.dumps(game.get("tags", [])),
        )
        for game in games
    ]

    with connect() as connection:
        connection.executemany(
            """
            INSERT INTO games (id, slug, name, released, year, metacritic,
                               playtime, rating, ratings_count, image, url,
                               platforms, genres, tags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                released=excluded.released,
                year=excluded.year,
                metacritic=excluded.metacritic,
                playtime=excluded.playtime,
                rating=excluded.rating,
                ratings_count=excluded.ratings_count,
                image=excluded.image,
                url=excluded.url,
                platforms=excluded.platforms,
                genres=excluded.genres,
                tags=excluded.tags
            """,
            rows,
        )
    return len(rows)


def load_games() -> list[dict]:
    """Read every game into a list of plain dictionaries."""
    init_db()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM games").fetchall()

    games = []
    for row in rows:
        game = dict(row)
        for column in JSON_COLUMNS:
            game[column] = json.loads(game[column])
        games.append(game)
    return games


def count_games() -> int:
    init_db()
    with connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM games").fetchone()[0]


def seed_if_empty() -> int:
    """
    Put the bundled demo catalogue in place on first run, so the app works
    the moment someone clones it — before they've signed up for an API key.
    Once they run the fetch script, real data replaces this.
    """
    if count_games() > 0:
        return 0
    if not SEED_PATH.exists():
        return 0

    games = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return save_games(games)
