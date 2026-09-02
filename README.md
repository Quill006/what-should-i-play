# What Should I Play?

Answer six questions, get three game recommendations. Press a button, get three more.

No account, no tracking, no algorithm you can't read. The entire scoring logic is one file you can open and change.

If you'd like to try it: https://what-should-i-play-nv92.onrender.com/
**[Türkçe](README.tr.md)**

---

## Run it

```bash
git clone https://github.com/Quill006/what-should-i-play.git
cd what-should-i-play

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

It works straight away using a small bundled demo catalogue of 40 games. To get real data, see below.

## Load real games

The catalogue comes from [RAWG](https://rawg.io), which publishes each game's Metacritic score in its API.

```bash
cp .env.example .env
# get a free key at https://rawg.io/apidocs and paste it into .env

python scripts/fetch_games.py --pages 50    # about 2,000 games
```

Restart the server to pick them up.

Useful flags:

```bash
python scripts/fetch_games.py --pages 125                  # ~5,000 games
python scripts/fetch_games.py --ordering -metacritic       # best reviewed first
python scripts/fetch_games.py --ordering -released         # newest first
```

### Why not scrape Metacritic directly?

Metacritic has no public API and its terms prohibit automated collection. Scraping it would also mean the project breaks every time their HTML changes — a bad deal for an open source repo where someone has to maintain the scraper.

RAWG republishes the Metacritic score as part of its own dataset, so you get the same number through a door that's open.

RAWG asks that you credit them and link back, and doesn't allow redistributing their data. That's why no database file is committed here — everyone fetches their own copy with their own key.

## How it works

```
  Browser                    FastAPI                  Engine
 ─────────                 ──────────               ──────────
 static/app.js  ──────►  GET /api/questions  ────►  questions.py
                ◄──────  questions + labels

 answers        ──────►  POST /api/recommend ────►  recommender.py
                ◄──────  3 games                    ▲
                                                    │
                                              SQLite (data/games.db)
                                                    ▲
                                          scripts/fetch_games.py ──► RAWG API
```

Recommendation happens in two stages, and the order matters.

**Stage one, hard filters.** A game is dropped outright if it's on the wrong platform, too long, too old, or missing a required tag. These aren't preferences — a PlayStation exclusive is not a *slightly worse* answer for someone who only owns a Switch, it's a wrong one. Folding this into the score as a penalty is the classic mistake: a highly-rated game overcomes the penalty and gets recommended to someone who can't play it.

**Stage two, scoring.** Whatever survived gets a number:

```
score =   0.45 × how many of your wanted tags it has
        + 0.20 × how many of your wanted genres it has
        + 0.30 × critic score / 100
        + 0.05 × novelty bonus if it's not a blockbuster
        − 0.15 × each tag you said you wanted to avoid
```

The weights live in [`app/config.py`](app/config.py). Change one, restart, see what happens.

### Metacritic is a quality filter, not a matching signal

This is the design decision that makes or breaks the project.

Critic scores answer "is this game good?" They say nothing about "is this game good *for you*". Rank by score alone and every user gets the same ten games — Zelda, Elden Ring, Baldur's Gate 3, forever.

So the score is only 30% of the weight, and it mostly acts as a tiebreaker between games that already match what you asked for. The matching itself is done by tags.

### Every recommendation explains itself

Each result carries the tags that earned it its place, shown as chips under the title. This isn't decoration: an unexplained recommendation is one users can't learn to trust, and one you can't debug. When a result looks wrong, the chips tell you which rule misfired.

## Project layout

```
app/
  config.py       scoring weights — the first place to experiment
  questions.py    the questions, in English and Turkish, with their effects
  recommender.py  filtering and scoring — the actual engine
  database.py     SQLite storage
  main.py         HTTP endpoints
scripts/
  fetch_games.py  downloads the catalogue from RAWG
  seed_data.json  40 demo games so the app runs before you have a key
static/           the web page: one HTML, one CSS, one JS file, no build step
```

## The API

Auto-generated docs at <http://127.0.0.1:8000/docs> — you can call every endpoint from the browser.

### `GET /api/questions?lang=en`

Returns the question flow and every UI label in the chosen language (`en` or `tr`). Answer option *effects* stay on the server, so scoring rules aren't something a client can tamper with.

### `POST /api/recommend`

```json
{
  "answers": { "platform": ["pc"], "mood": ["relaxing"], "time": ["short"] },
  "offset": 0,
  "lang": "en"
}
```

Returns three games plus `total` and `has_more`. The "show 3 more" button is just this call with `offset: 3`, then `6`, then `9`. Ranking is deterministic and ties break on game id, so page two never repeats or skips a game — no server-side session needed.

## Adding a question

Questions are data, not code. Add an entry to `QUESTIONS` in `app/questions.py`:

```python
{
    "id": "vibe",
    "type": "single",          # or "multi"
    "required": True,
    "text": {"en": "Realistic or stylised?", "tr": "Gerçekçi mi, stilize mi?"},
    "options": [
        {
            "id": "stylised",
            "label": {"en": "Stylised", "tr": "Stilize"},
            "effects": {"want_tags": ["pixel-graphics", "cartoon", "hand-drawn"]},
        },
    ],
}
```

The engine has no `if answer == "stylised"` branch anywhere — it just collects effects from whatever the user picked. Available effect keys are documented at the top of `questions.py`.

## Adding a language

1. Add the code to `SUPPORTED_LANGUAGES` in `app/questions.py`
2. Add your translations to every `{"en": ..., "tr": ...}` block in that file
3. Add a button to the language switcher in `static/index.html`

No other file needs to change. The engine works on tag slugs, which aren't translated; only the labels shown to users are.

## Things worth building next

- Collect thumbs up/down on results and use it to tune the weights
- "Games like X" — ask for a favourite, match against its tag vector
- Filter out games the user has already played
- Steam tags as a second data source; they're richer than genres
- A CLI version, for people who'd rather not run a browser

Pull requests welcome, including ones that just argue the weights are wrong.

## Licence

MIT. Game data belongs to RAWG and is used under their API terms.
