"""
Fill the local database with real games from RAWG.

Why RAWG and not Metacritic: Metacritic has no public API and its terms
forbid automated collection. RAWG publishes each game's Metacritic score in
its own API, so you get the same number through a door that's actually open.

    Get a free key: https://rawg.io/apidocs
    Put it in .env as RAWG_API_KEY=...
    Then run: python scripts/fetch_games.py

RAWG's terms: free for personal use and for projects under 100k monthly
users, but you must credit RAWG and link back, and you may not redistribute
the data. That last point is why this repository ships no database file —
everyone fetches their own copy.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests

# Let the script import from app/ when run as `python scripts/fetch_games.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import database  # noqa: E402

API_URL = "https://api.rawg.io/api/games"
PAGE_SIZE = 40  # RAWG's maximum
SECONDS_BETWEEN_REQUESTS = 0.5  # be a polite guest on someone else's server


def load_api_key() -> str:
    """Read RAWG_API_KEY from the environment, falling back to a .env file."""
    key = os.environ.get("RAWG_API_KEY")
    if key:
        return key

    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("RAWG_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")

    sys.exit(
        "No API key found.\n"
        "  1. Get one at https://rawg.io/apidocs\n"
        "  2. Copy .env.example to .env\n"
        "  3. Put your key in it as RAWG_API_KEY=your_key_here"
    )


def normalise(raw: dict) -> dict:
    """
    Flatten one RAWG game into the shape our database expects.

    RAWG nests things: platforms arrive as [{"platform": {"name": "PC"}}].
    Doing this conversion once, here, means the rest of the codebase never
    has to know what RAWG's JSON looks like. If you later swap to IGDB, this
    function is the only thing you rewrite.
    """
    return {
        "id": raw["id"],
        "slug": raw.get("slug"),
        "name": raw["name"],
        "released": raw.get("released"),
        "metacritic": raw.get("metacritic"),
        "playtime": raw.get("playtime"),
        "rating": raw.get("rating"),
        "ratings_count": raw.get("ratings_count"),
        "image": raw.get("background_image"),
        "url": f"https://rawg.io/games/{raw['slug']}" if raw.get("slug") else None,
        "platforms": [
            entry["platform"]["name"]
            for entry in (raw.get("platforms") or [])
            if entry.get("platform")
        ],
        "genres": [genre["name"] for genre in (raw.get("genres") or [])],
        "tags": [
            tag["slug"]
            for tag in (raw.get("tags") or [])
            # RAWG carries tags in many languages; the English ones are the
            # slugs our questions are written against.
            if tag.get("language") == "eng" and tag.get("slug")
        ],
    }


def fetch_page(session: requests.Session, key: str, page: int, ordering: str) -> dict:
    response = session.get(
        API_URL,
        params={
            "key": key,
            "page": page,
            "page_size": PAGE_SIZE,
            "ordering": ordering,
        },
        timeout=30,
    )

    if response.status_code == 401:
        sys.exit("RAWG rejected the key. Check RAWG_API_KEY in your .env file.")
    if response.status_code == 429:
        print("  Rate limited. Waiting 60 seconds…")
        time.sleep(60)
        return fetch_page(session, key, page, ordering)

    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download games from RAWG.")
    parser.add_argument(
        "--pages",
        type=int,
        default=50,
        help="Pages to fetch, 40 games each. Default 50 (~2000 games).",
    )
    parser.add_argument(
        "--ordering",
        default="-added",
        help="RAWG sort order. -added is most-saved-by-users, -metacritic is best-reviewed.",
    )
    parser.add_argument(
        "--keep-demo-data",
        action="store_true",
        help="Don't clear the bundled demo games before importing.",
    )
    args = parser.parse_args()

    key = load_api_key()
    database.init_db()

    if not args.keep_demo_data:
        with database.connect() as connection:
            connection.execute("DELETE FROM games")
        print("Cleared existing games.")

    session = requests.Session()
    total_saved = 0

    for page in range(1, args.pages + 1):
        print(f"Page {page}/{args.pages}…", end=" ", flush=True)
        payload = fetch_page(session, key, page, args.ordering)

        results = payload.get("results", [])
        if not results:
            print("no more results.")
            break

        games = [normalise(raw) for raw in results]
        total_saved += database.save_games(games)
        print(f"{len(games)} games (running total {total_saved})")

        if not payload.get("next"):
            break
        time.sleep(SECONDS_BETWEEN_REQUESTS)

    print(f"\nDone. {database.count_games()} games in the database.")
    print("Restart the server to pick them up.")


if __name__ == "__main__":
    main()
