"""
The web layer.

FastAPI's job here is narrow: read the request, hand it to the engine, send
the answer back as JSON. All the actual thinking lives in recommender.py, so
you could swap FastAPI for Flask or a command-line script without touching a
line of the scoring logic. Keep it that way.

Run it with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000 for the app, or
http://127.0.0.1:8000/docs for the auto-generated API documentation, where
you can call every endpoint from the browser.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import config, database
from app.questions import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    questions_for,
    tag_label,
    ui_strings_for,
)
from app.recommender import build_preferences, recommend

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# The catalogue, held in memory. Loaded once at startup — see the note in
# database.py about why we don't score in SQL.
CATALOGUE: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts, and once when it shuts down."""
    seeded = database.seed_if_empty()
    if seeded:
        print(f"Seeded the database with {seeded} demo games.")

    CATALOGUE.extend(database.load_games())
    print(f"Loaded {len(CATALOGUE)} games.")
    if not CATALOGUE:
        print("Catalogue is empty. Run: python scripts/fetch_games.py")

    yield  # the app serves requests here

    CATALOGUE.clear()


app = FastAPI(
    title="What Should I Play?",
    description="Answer a few questions, get game recommendations.",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Request and response shapes -------------------------------------------
# Pydantic models double as validation and as documentation. If a request
# doesn't match, FastAPI rejects it with a clear 422 before your code runs.


class RecommendRequest(BaseModel):
    answers: dict[str, list[str]] = Field(
        ...,
        description='Question id to chosen option ids, e.g. {"mood": ["relaxing"]}',
        examples=[{"platform": ["pc"], "mood": ["relaxing"], "time": ["short"]}],
    )
    offset: int = Field(
        0,
        ge=0,
        description="Skip this many results. The 'show 3 more' button sends 3, then 6, then 9.",
    )
    lang: str = Field(DEFAULT_LANGUAGE, description="en or tr")


class GameOut(BaseModel):
    id: int
    name: str
    year: int | None = None
    metacritic: int | None = None
    playtime: int | None = None
    image: str | None = None
    url: str | None = None
    genres: list[str] = []
    match_percent: int
    reasons: list[str] = []


class RecommendResponse(BaseModel):
    games: list[GameOut]
    total: int
    offset: int
    has_more: bool


# --- Endpoints --------------------------------------------------------------


def check_language(lang: str) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang}'. Use one of: {', '.join(SUPPORTED_LANGUAGES)}",
        )
    return lang


@app.get("/api/questions", tags=["questions"])
def get_questions(lang: str = Query(DEFAULT_LANGUAGE, description="en or tr")):
    """The question flow and every UI label, in the requested language."""
    check_language(lang)
    return {
        "lang": lang,
        "questions": questions_for(lang),
        "ui": ui_strings_for(lang),
    }


@app.post("/api/recommend", response_model=RecommendResponse, tags=["recommendations"])
def post_recommend(request: RecommendRequest):
    """
    Score the whole catalogue against the answers and return one page.

    Ranking is deterministic, so asking for offset=3 gives you the next three
    games with no repeats — that's all the "show 3 more" button does.
    """
    check_language(request.lang)

    if not CATALOGUE:
        raise HTTPException(
            status_code=503,
            detail="No games loaded. Run: python scripts/fetch_games.py",
        )

    prefs = build_preferences(request.answers)
    page, total = recommend(
        CATALOGUE, prefs, offset=request.offset, limit=config.PAGE_SIZE
    )

    games = [
        GameOut(
            id=game["id"],
            name=game["name"],
            year=game.get("year"),
            metacritic=game.get("metacritic"),
            playtime=game.get("playtime"),
            image=game.get("image"),
            url=game.get("url"),
            genres=game.get("genres", []),
            match_percent=game["match_percent"],
            # Translate the raw tag slugs into readable phrases here, at the
            # edge — the engine stays language-agnostic.
            reasons=[tag_label(tag, request.lang) for tag in game["matched_tags"][:4]],
        )
        for game in page
    ]

    return RecommendResponse(
        games=games,
        total=total,
        offset=request.offset,
        has_more=request.offset + len(games) < total,
    )


@app.get("/api/stats", tags=["meta"])
def get_stats():
    """Handy for checking your data actually loaded."""
    with_scores = [g for g in CATALOGUE if g.get("metacritic")]
    return {
        "games": len(CATALOGUE),
        "with_critic_score": len(with_scores),
        "average_critic_score": (
            round(sum(g["metacritic"] for g in with_scores) / len(with_scores), 1)
            if with_scores
            else None
        ),
    }


# --- Serving the web page ---------------------------------------------------
# Mounted last so it doesn't shadow the /api routes above.

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
