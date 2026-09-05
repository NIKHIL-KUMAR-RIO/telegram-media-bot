import re

QUALITY_PATTERN = r"(?P<quality>480p|720p|1080p|2160p|4k)"
PART_PATTERN = r"(?:Part\s?(?P<part>\d+))?"

# Show patterns, tried in order. Supports:
#   Title.S01E05.720p                (standard)
#   Title.S01E05.Part.2.720p         (multi-part episode, e.g. a 2-part finale)
#   Title.1x05.720p                  (alt "1x05" format)
#   Title.Season 1 Episode 5         (wordy format)
SHOW_PATTERNS = [
    re.compile(
        rf"^(?P<title>.+?)\sS(?P<s>\d{{1,2}})E(?P<e1>\d{{1,2}})(?:E(?P<e2>\d{{1,2}}))?\s*{PART_PATTERN}\s*{QUALITY_PATTERN}?\s*$",
        re.IGNORECASE
    ),
    re.compile(
        rf"^(?P<title>.+?)\s(?P<s>\d{{1,2}})x(?P<e1>\d{{1,2}})(?:x(?P<e2>\d{{1,2}}))?\s*{PART_PATTERN}\s*{QUALITY_PATTERN}?\s*$",
        re.IGNORECASE
    ),
    re.compile(
        rf"^(?P<title>.+?)\sSeason\s(?P<s>\d{{1,2}})\sEpisode\s(?P<e1>\d{{1,2}})\s*{PART_PATTERN}\s*{QUALITY_PATTERN}?\s*$",
        re.IGNORECASE
    ),
]

# Movie pattern. Supports year plain, in (parens), or in [brackets].
# Year is restricted to 19xx/20xx to avoid confusing a quality tag
# (e.g. 2160p) or a title-embedded number for a year.
MOVIE_PATTERN = re.compile(
    r"^(?P<title>.+?)\s[\(\[]?(?P<year>(?:19|20)\d{2})[\)\]]?\s*"
    rf"{QUALITY_PATTERN}?\s*$",
    re.IGNORECASE
)


def clean(name):
    # Normalize all common separator styles down to plain spaces.
    name = name.replace(".", " ").replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse(filename):
    # Remove file extension
    name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", filename)
    name = clean(name)

    # Try show patterns first
    for pattern in SHOW_PATTERNS:
        s = pattern.match(name)
        if s:
            groups = s.groupdict()
            ep1 = int(s.group("e1"))
            ep2 = int(s.group("e2")) if groups.get("e2") else None
            part = int(groups["part"]) if groups.get("part") else None

            return {
                "valid": True,
                "type": "show",
                "title": clean(s.group("title")),
                "year": None,
                "season": int(s.group("s")),
                "episode_start": ep1,
                "episode_end": ep2,
                "part": part,
                "quality": s.group("quality").lower() if s.group("quality") else "unknown"
            }

    # Then try movie pattern
    m = MOVIE_PATTERN.match(name)
    if m:
        title = clean(m.group("title"))
        return {
            "valid": True,
            "type": "movie",
            "title": title,
            "year": m.group("year"),
            "season": None,
            "episode_start": None,
            "episode_end": None,
            "part": None,
            "quality": m.group("quality").lower() if m.group("quality") else "unknown",
            # Auto-tag as LEGO if the title contains "lego" anywhere.
            # Admin can override this later via /rename.
            "category": "lego" if "lego" in title.lower() else "movie"
        }

    return {
        "valid": False,
        "reason": f"Could not auto-parse filename: {filename}"
    }
