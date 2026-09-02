"""
Tunable settings for the recommendation engine.

Everything that affects *how* games are ranked lives here, so you can
experiment without touching the engine itself. Try changing a weight,
restart the server, and see how the results shift.
"""

# How much each signal contributes to a game's final score.
# These should roughly add up to 1.0 to keep scores in a readable 0-1 range.
WEIGHTS = {
    "tags": 0.45,     # how well the game's tags match what the user asked for
    "genres": 0.20,   # how well the genres match
    "quality": 0.30,  # critic score (Metacritic), normalised to 0-1
    "novelty": 0.05,  # small boost for lesser-known games, to avoid always
                      # recommending the same ten blockbusters
}

# Subtracted from the score for each tag the user said they wanted to avoid.
AVOID_TAG_PENALTY = 0.15

# Used when a game has no Metacritic score at all. 70 is deliberately
# mediocre: an unrated game shouldn't beat a well-reviewed one by default.
DEFAULT_METACRITIC = 70

# Games with fewer ratings than this count as "lesser known" and get the
# novelty boost.
NOVELTY_THRESHOLD = 4000

# Games below this critic score are dropped entirely. Set to 0 to disable.
MINIMUM_METACRITIC = 60

# How many games each request returns. The "show me 3 more" button works by
# asking for the same list with a larger offset.
PAGE_SIZE = 3
