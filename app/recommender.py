"""
The recommendation engine.

Two stages, in this order:

  1. Hard filters  — remove games that simply won't work (wrong platform,
                     too long, too old). A game either passes or it's gone.
  2. Soft scoring  — rank whatever survived. Every remaining game gets a
                     number between roughly 0 and 1, and we sort by it.

Keeping these separate matters. If you fold "wrong platform" into the score
as a penalty, a brilliant PlayStation exclusive can still out-score a decent
PC game and end up recommended to someone who owns neither console.
"""

from dataclasses import dataclass, field

from app import config
from app.questions import PLATFORM_FAMILIES, QUESTIONS


@dataclass
class Preferences:
    """Everything we learned from the user's answers, in one object."""

    platforms: set[str] = field(default_factory=set)   # concrete platform names
    max_playtime: int | None = None
    min_year: int | None = None
    want_tags: set[str] = field(default_factory=set)
    avoid_tags: set[str] = field(default_factory=set)
    want_genres: set[str] = field(default_factory=set)
    # A list of tag groups. The game must satisfy every group by carrying at
    # least one tag from it. Two groups means two separate requirements.
    require_any_tags: list[set[str]] = field(default_factory=list)


def build_preferences(answers: dict[str, list[str]]) -> Preferences:
    """
    Turn `{"mood": ["relaxing"], "platform": ["pc", "nintendo"]}` into a
    Preferences object, by looking up the effects of each chosen option.

    Unknown question or option ids are ignored rather than raising. A stale
    bookmark shouldn't crash the server.
    """
    prefs = Preferences()

    for question in QUESTIONS:
        chosen_ids = answers.get(question["id"], [])
        if not chosen_ids:
            continue

        for option in question["options"]:
            if option["id"] not in chosen_ids:
                continue

            effects = option["effects"]

            for family in effects.get("platform_family", []):
                prefs.platforms.update(PLATFORM_FAMILIES.get(family, []))

            prefs.want_tags.update(effects.get("want_tags", []))
            prefs.avoid_tags.update(effects.get("avoid_tags", []))
            prefs.want_genres.update(effects.get("want_genres", []))

            if "require_any_tags" in effects:
                prefs.require_any_tags.append(set(effects["require_any_tags"]))

            # When two options both set a limit, keep the stricter one.
            if "max_playtime" in effects:
                current = prefs.max_playtime
                prefs.max_playtime = min(current or 10**6, effects["max_playtime"])
            if "min_year" in effects:
                prefs.min_year = max(prefs.min_year or 0, effects["min_year"])

    # A tag can't be both wanted and avoided. Wanting wins — it came from a
    # more specific answer.
    prefs.avoid_tags -= prefs.want_tags

    return prefs


def passes_filters(game: dict, prefs: Preferences) -> bool:
    """Stage one: is this game even a candidate?"""

    if prefs.platforms and not (set(game["platforms"]) & prefs.platforms):
        return False

    game_tags = set(game["tags"])
    for required_group in prefs.require_any_tags:
        if not (game_tags & required_group):
            return False

    if prefs.min_year and game.get("year") and game["year"] < prefs.min_year:
        return False

    if prefs.max_playtime and game.get("playtime"):
        # 1.3x slack: "average playtime" is a rough number, and a 12-hour game
        # is still a reasonable answer to "an evening or two".
        if game["playtime"] > prefs.max_playtime * 1.3:
            return False

    metacritic = game.get("metacritic")
    if metacritic and metacritic < config.MINIMUM_METACRITIC:
        return False

    return True


def overlap_ratio(have: set[str], want: set[str]) -> float:
    """
    What share of the things the user asked for does this game actually have?

    Deliberately *not* Jaccard similarity. Jaccard divides by the union, which
    punishes games for having lots of extra tags — so a rich, well-tagged game
    scores worse than a thin one. Here the denominator is only what the user
    asked for, so extra tags are free.
    """
    if not want:
        return 0.0
    return len(have & want) / len(want)


def score_game(game: dict, prefs: Preferences) -> tuple[float, list[str]]:
    """
    Stage two: score a candidate, and report which tags earned it the score.

    Returns (score, matched_tags). The matched tags are what the UI shows in
    the "why this one" line — an unexplained recommendation is one the user
    can't learn to trust or correct.
    """
    game_tags = set(game["tags"])
    game_genres = set(game["genres"])

    tag_score = overlap_ratio(game_tags, prefs.want_tags)
    genre_score = overlap_ratio(game_genres, prefs.want_genres)

    metacritic = game.get("metacritic") or config.DEFAULT_METACRITIC
    quality_score = metacritic / 100

    is_obscure = (game.get("ratings_count") or 0) < config.NOVELTY_THRESHOLD
    novelty_score = 1.0 if is_obscure else 0.0

    score = (
        config.WEIGHTS["tags"] * tag_score
        + config.WEIGHTS["genres"] * genre_score
        + config.WEIGHTS["quality"] * quality_score
        + config.WEIGHTS["novelty"] * novelty_score
    )

    score -= config.AVOID_TAG_PENALTY * len(game_tags & prefs.avoid_tags)

    matched = sorted(game_tags & prefs.want_tags)
    return score, matched


def recommend(
    games: list[dict],
    prefs: Preferences,
    offset: int = 0,
    limit: int = config.PAGE_SIZE,
) -> tuple[list[dict], int]:
    """
    Rank every game and return one page of results.

    The "show 3 more" button works by calling this again with offset=3, 6, 9…
    Scoring is deterministic and the tiebreaker is the game id, so the ranking
    is identical every time — page two never repeats or skips a game.

    Returns (page_of_results, total_matches).
    """
    scored = []
    for game in games:
        if not passes_filters(game, prefs):
            continue
        score, matched = score_game(game, prefs)
        scored.append((score, game, matched))

    # Sort by score, high to low. Ties break on game id so the order is stable.
    scored.sort(key=lambda row: (-row[0], row[1]["id"]))

    page = []
    for score, game, matched in scored[offset : offset + limit]:
        page.append(
            {
                **game,
                "score": round(score, 4),
                "match_percent": max(0, min(100, round(score * 100))),
                "matched_tags": matched,
            }
        )

    return page, len(scored)
