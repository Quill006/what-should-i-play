"""
The questions we ask the user, in English and Turkish.

Design note: each answer option carries its own "effects" — the changes it
makes to the search. The engine never contains an `if answer == "cozy"`
branch; it just collects effects from whatever the user picked. That means
adding a new question is a pure data change, no engine code required.

Effect keys
-----------
platform_family : hard filter. Game must be on at least one chosen platform.
max_playtime    : hard filter. Game's average playtime in hours must be under this.
min_year        : hard filter. Game must be released on or after this year.
want_tags       : soft signal. Matching tags raise the score.
want_genres     : soft signal. Matching genres raise the score.
avoid_tags      : soft signal. Matching tags lower the score.
require_any_tags: hard filter. Game must carry at least one of these tags.

The last one exists because some answers are constraints, not preferences.
"We're on the same couch" is a fact about the room; a single-player game is
not a worse answer to it, it's a wrong one. Left as a soft signal it loses
to a highly-rated solo game, which is exactly the failure this avoids. Use
it sparingly — every hard filter is a way to end up with no results at all.
"""

SUPPORTED_LANGUAGES = ("en", "tr")
DEFAULT_LANGUAGE = "en"

# RAWG reports platforms as specific model names. We group them into families
# so the user picks "PlayStation" rather than five separate console entries.
PLATFORM_FAMILIES = {
    "pc": ["PC", "macOS", "Linux"],
    "playstation": ["PlayStation 5", "PlayStation 4", "PlayStation 3", "PS Vita"],
    "xbox": ["Xbox Series S/X", "Xbox One", "Xbox 360"],
    "nintendo": ["Nintendo Switch", "Nintendo Switch 2", "Nintendo 3DS", "Wii U", "Wii"],
    "mobile": ["iOS", "Android"],
}

QUESTIONS = [
    {
        "id": "platform",
        "type": "multi",
        "required": True,
        "text": {
            "en": "What do you play on?",
            "tr": "Hangi platformda oynuyorsun?",
        },
        "hint": {
            "en": "Pick every device you have access to.",
            "tr": "Erişimin olan tüm cihazları seç.",
        },
        "options": [
            {
                "id": "pc",
                "label": {"en": "PC", "tr": "PC"},
                "effects": {"platform_family": ["pc"]},
            },
            {
                "id": "playstation",
                "label": {"en": "PlayStation", "tr": "PlayStation"},
                "effects": {"platform_family": ["playstation"]},
            },
            {
                "id": "xbox",
                "label": {"en": "Xbox", "tr": "Xbox"},
                "effects": {"platform_family": ["xbox"]},
            },
            {
                "id": "nintendo",
                "label": {"en": "Nintendo", "tr": "Nintendo"},
                "effects": {"platform_family": ["nintendo"]},
            },
            {
                "id": "mobile",
                "label": {"en": "Phone or tablet", "tr": "Telefon veya tablet"},
                "effects": {"platform_family": ["mobile"]},
            },
        ],
    },
    {
        "id": "time",
        "type": "single",
        "required": True,
        "text": {
            "en": "How much time do you want to put in?",
            "tr": "Ne kadar vakit ayırabilirsin?",
        },
        "options": [
            {
                "id": "short",
                "label": {"en": "An evening or two", "tr": "Bir iki akşam"},
                "effects": {"max_playtime": 10, "want_tags": ["short", "casual"]},
            },
            {
                "id": "medium",
                "label": {"en": "A couple of weeks", "tr": "Birkaç hafta"},
                "effects": {"max_playtime": 35},
            },
            {
                "id": "long",
                "label": {"en": "I want something huge", "tr": "Uzun soluklu olsun"},
                "effects": {"want_tags": ["open-world", "sandbox", "rpg"]},
            },
            {
                "id": "any",
                "label": {"en": "Doesn't matter", "tr": "Fark etmez"},
                "effects": {},
            },
        ],
    },
    {
        "id": "mood",
        "type": "single",
        "required": True,
        "text": {
            "en": "What are you in the mood for?",
            "tr": "Nasıl bir şey istiyorsun?",
        },
        "options": [
            {
                "id": "relaxing",
                "label": {"en": "Something calm", "tr": "Sakin bir şey"},
                "effects": {
                    "want_tags": ["relaxing", "cozy", "atmospheric", "casual", "exploration"],
                    "avoid_tags": ["difficult", "souls-like", "horror", "competitive"],
                },
            },
            {
                "id": "challenging",
                "label": {"en": "A real challenge", "tr": "Beni zorlasın"},
                "effects": {
                    "want_tags": ["difficult", "souls-like", "roguelike", "strategy"],
                    "avoid_tags": ["casual", "relaxing"],
                },
            },
            {
                "id": "story",
                "label": {"en": "A good story", "tr": "İyi bir hikâye"},
                "effects": {
                    "want_tags": ["story-rich", "singleplayer", "atmospheric", "choices-matter"],
                    "avoid_tags": ["competitive", "pvp"],
                },
            },
            {
                "id": "competitive",
                "label": {"en": "Beating other people", "tr": "Rekabet"},
                "effects": {
                    "want_tags": ["competitive", "pvp", "multiplayer", "shooter"],
                    "avoid_tags": ["relaxing", "story-rich"],
                },
            },
        ],
    },
    {
        "id": "company",
        "type": "single",
        "required": True,
        "text": {
            "en": "Who are you playing with?",
            "tr": "Kiminle oynayacaksın?",
        },
        "options": [
            {
                "id": "alone",
                "label": {"en": "On my own", "tr": "Tek başıma"},
                "effects": {"want_tags": ["singleplayer"], "avoid_tags": ["pvp", "mmo"]},
            },
            {
                "id": "coop",
                "label": {"en": "With a friend", "tr": "Bir arkadaşımla"},
                "effects": {
                    "want_tags": ["co-op", "online-co-op", "multiplayer"],
                    "require_any_tags": ["co-op", "online-co-op", "multiplayer", "pvp"],
                },
            },
            {
                "id": "couch",
                "label": {"en": "Same room, same screen", "tr": "Aynı odada, aynı ekranda"},
                "effects": {
                    "want_tags": ["local-co-op", "local-multiplayer", "split-screen", "co-op"],
                    "require_any_tags": ["local-co-op", "local-multiplayer", "split-screen"],
                },
            },
            {
                "id": "any",
                "label": {"en": "Doesn't matter", "tr": "Fark etmez"},
                "effects": {},
            },
        ],
    },
    {
        "id": "genre",
        "type": "multi",
        "required": False,
        "text": {
            "en": "Any genres you lean towards?",
            "tr": "Sevdiğin türler var mı?",
        },
        "hint": {
            "en": "Optional. Skip it and we'll go by mood alone.",
            "tr": "İsteğe bağlı. Boş bırakırsan sadece ruh haline göre bakarız.",
        },
        "options": [
            {
                "id": "action",
                "label": {"en": "Action", "tr": "Aksiyon"},
                "effects": {"want_genres": ["Action", "Shooter", "Fighting"]},
            },
            {
                "id": "rpg",
                "label": {"en": "Role-playing", "tr": "Rol yapma"},
                "effects": {"want_genres": ["RPG"], "want_tags": ["rpg"]},
            },
            {
                "id": "strategy",
                "label": {"en": "Strategy", "tr": "Strateji"},
                "effects": {"want_genres": ["Strategy"], "want_tags": ["turn-based", "tactical"]},
            },
            {
                "id": "puzzle",
                "label": {"en": "Puzzle", "tr": "Bulmaca"},
                "effects": {"want_genres": ["Puzzle"], "want_tags": ["puzzle"]},
            },
            {
                "id": "simulation",
                "label": {"en": "Simulation", "tr": "Simülasyon"},
                "effects": {"want_genres": ["Simulation"], "want_tags": ["building", "management"]},
            },
            {
                "id": "horror",
                "label": {"en": "Horror", "tr": "Korku"},
                "effects": {"want_tags": ["horror", "survival-horror"]},
            },
            {
                "id": "platformer",
                "label": {"en": "Platformer", "tr": "Platform"},
                "effects": {"want_genres": ["Platformer", "Arcade"], "want_tags": ["platformer"]},
            },
            {
                "id": "racing",
                "label": {"en": "Racing & sports", "tr": "Yarış ve spor"},
                "effects": {"want_genres": ["Racing", "Sports"]},
            },
        ],
    },
    {
        "id": "era",
        "type": "single",
        "required": True,
        "text": {
            "en": "How old is too old?",
            "tr": "Eski oyunlara açık mısın?",
        },
        "options": [
            {
                "id": "recent",
                "label": {"en": "Last few years only", "tr": "Sadece son birkaç yıl"},
                "effects": {"min_year": 2021},
            },
            {
                "id": "modern",
                "label": {"en": "Nothing before 2015", "tr": "2015 sonrası olsun"},
                "effects": {"min_year": 2015},
            },
            {
                "id": "any",
                "label": {"en": "Age doesn't bother me", "tr": "Yaşı önemli değil"},
                "effects": {},
            },
        ],
    },
]

# Short, human-readable labels for the tags we surface in the "why this game"
# explanation. Anything not listed here falls back to the raw tag name.
TAG_LABELS = {
    "story-rich": {"en": "strong story", "tr": "güçlü hikâye"},
    "open-world": {"en": "open world", "tr": "açık dünya"},
    "co-op": {"en": "co-op", "tr": "işbirlikli"},
    "online-co-op": {"en": "online co-op", "tr": "çevrimiçi işbirlikli"},
    "local-co-op": {"en": "local co-op", "tr": "yerel işbirlikli"},
    "local-multiplayer": {"en": "local multiplayer", "tr": "yerel çok oyunculu"},
    "split-screen": {"en": "split screen", "tr": "bölünmüş ekran"},
    "singleplayer": {"en": "single player", "tr": "tek oyunculu"},
    "multiplayer": {"en": "multiplayer", "tr": "çok oyunculu"},
    "difficult": {"en": "difficult", "tr": "zorlu"},
    "souls-like": {"en": "souls-like", "tr": "souls tarzı"},
    "relaxing": {"en": "relaxing", "tr": "rahatlatıcı"},
    "cozy": {"en": "cozy", "tr": "huzurlu"},
    "atmospheric": {"en": "atmospheric", "tr": "atmosferik"},
    "casual": {"en": "easy to pick up", "tr": "rahat oynanır"},
    "competitive": {"en": "competitive", "tr": "rekabetçi"},
    "roguelike": {"en": "roguelike", "tr": "roguelike"},
    "exploration": {"en": "exploration", "tr": "keşif"},
    "short": {"en": "short", "tr": "kısa"},
    "horror": {"en": "horror", "tr": "korku"},
    "survival-horror": {"en": "survival horror", "tr": "hayatta kalma korkusu"},
    "puzzle": {"en": "puzzle", "tr": "bulmaca"},
    "turn-based": {"en": "turn-based", "tr": "sıra tabanlı"},
    "tactical": {"en": "tactical", "tr": "taktiksel"},
    "sandbox": {"en": "sandbox", "tr": "sandbox"},
    "rpg": {"en": "RPG", "tr": "RPG"},
    "choices-matter": {"en": "choices matter", "tr": "kararlar önemli"},
    "pvp": {"en": "PvP", "tr": "PvP"},
    "shooter": {"en": "shooter", "tr": "nişancı"},
    "platformer": {"en": "platformer", "tr": "platform"},
    "building": {"en": "building", "tr": "inşa"},
    "management": {"en": "management", "tr": "yönetim"},
    "mmo": {"en": "MMO", "tr": "MMO"},
    "strategy": {"en": "strategy", "tr": "strateji"},
    "metroidvania": {"en": "metroidvania", "tr": "metroidvania"},
    "survival": {"en": "survival", "tr": "hayatta kalma"},
    "crafting": {"en": "crafting", "tr": "üretim"},
    "stealth": {"en": "stealth", "tr": "gizlilik"},
    "funny": {"en": "funny", "tr": "eğlenceli"},
    "farming": {"en": "farming", "tr": "çiftçilik"},
    "fantasy": {"en": "fantasy", "tr": "fantastik"},
    "sci-fi": {"en": "sci-fi", "tr": "bilim kurgu"},
    "battle-royale": {"en": "battle royale", "tr": "battle royale"},
    "family-friendly": {"en": "family friendly", "tr": "aileye uygun"},
    "great-soundtrack": {"en": "great soundtrack", "tr": "harika müzikler"},
    "pixel-graphics": {"en": "pixel art", "tr": "piksel grafik"},
    "replay-value": {"en": "worth replaying", "tr": "tekrar oynanır"},
    "free-to-play": {"en": "free to play", "tr": "ücretsiz"},
    "first-person": {"en": "first person", "tr": "birinci şahıs"},
    "third-person": {"en": "third person", "tr": "üçüncü şahıs"},
    "detective": {"en": "detective work", "tr": "dedektiflik"},
    "fast-paced": {"en": "fast paced", "tr": "hızlı tempolu"},
}

# Everything the UI needs that isn't a question.
UI_STRINGS = {
    "title": {"en": "What should I play?", "tr": "Ne oynasam?"},
    "subtitle": {
        "en": "Six questions. Three games. No account, no tracking.",
        "tr": "Altı soru. Üç oyun. Hesap yok, takip yok.",
    },
    "start": {"en": "Start", "tr": "Başla"},
    "next": {"en": "Next", "tr": "Devam"},
    "back": {"en": "Back", "tr": "Geri"},
    "finish": {"en": "Show me games", "tr": "Oyunları göster"},
    "more": {"en": "Show 3 more", "tr": "3 tane daha göster"},
    "restart": {"en": "Start over", "tr": "Baştan başla"},
    "why": {"en": "Why this one", "tr": "Neden bu"},
    "score": {"en": "Critic score", "tr": "Eleştirmen puanı"},
    "hours": {"en": "hours", "tr": "saat"},
    "loading": {"en": "Looking…", "tr": "Bakıyorum…"},
    "empty": {
        "en": "Nothing left that fits. Loosen a filter and try again.",
        "tr": "Uyan başka oyun kalmadı. Bir filtreyi gevşetip tekrar dene.",
    },
    "error": {
        "en": "The server didn't respond. Check that it's running.",
        "tr": "Sunucu cevap vermedi. Çalıştığından emin ol.",
    },
    "select_one": {"en": "Pick at least one", "tr": "En az bir tane seç"},
    "of": {"en": "of", "tr": "/"},
    "match": {"en": "match", "tr": "uyum"},
}


def localise(block: dict, lang: str) -> str:
    """Pull one language out of a {"en": ..., "tr": ...} block."""
    return block.get(lang) or block.get(DEFAULT_LANGUAGE, "")


def questions_for(lang: str) -> list[dict]:
    """
    Flatten the question list into plain text for one language.

    The frontend never sees the "effects" — those stay on the server, so the
    scoring rules aren't something a user can tamper with.
    """
    result = []
    for question in QUESTIONS:
        result.append(
            {
                "id": question["id"],
                "type": question["type"],
                "required": question["required"],
                "text": localise(question["text"], lang),
                "hint": localise(question.get("hint", {}), lang) or None,
                "options": [
                    {"id": option["id"], "label": localise(option["label"], lang)}
                    for option in question["options"]
                ],
            }
        )
    return result


def tag_label(tag: str, lang: str) -> str:
    """Turn a raw tag slug into something readable."""
    if tag in TAG_LABELS:
        return localise(TAG_LABELS[tag], lang)
    return tag.replace("-", " ")


def ui_strings_for(lang: str) -> dict:
    return {key: localise(block, lang) for key, block in UI_STRINGS.items()}
