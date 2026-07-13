import re

# Matches: Show.Title.S01E01E02.1080p or Show.Title.S01E01.720p
SHOW = re.compile(
    r"^(?P<title>.+?)[.\s]S(?P<s>\d{2})E(?P<e1>\d{2})(?:E(?P<e2>\d{2}))?[.\s]*(?P<quality>480p|720p|1080p|2160p|4k)?[.\s]*$",
    re.IGNORECASE
)

# Matches: Movie.Title.2008.1080p or Movie.Title.(2008).1080p
MOVIE = re.compile(
    r"^(?P<title>.+?)[.\s]\(?(?P<year>\d{4})\)?[.\s]*(?P<quality>480p|720p|1080p|2160p|4k)?[.\s]*$",
    re.IGNORECASE
)


def clean(name):
    name = name.replace(".", " ").replace("_", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse(filename):
    # Remove file extension
    name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", filename)
    name = clean(name)

    # Check show first
    s = SHOW.match(name)
    if s:
        ep1 = int(s.group("e1"))
        ep2 = int(s.group("e2")) if s.group("e2") else None

        return {
            "valid": True,
            "type": "show",
            "title": clean(s.group("title")),
            "year": None,
            "season": int(s.group("s")),
            "episode_start": ep1,
            "episode_end": ep2,
            "quality": s.group("quality").lower() if s.group("quality") else "unknown"
        }

    # Check movie
    m = MOVIE.match(name)
    if m:
        return {
            "valid": True,
            "type": "movie",
            "title": clean(m.group("title")),
            "year": m.group("year"),
            "season": None,
            "episode_start": None,
            "episode_end": None,
            "quality": m.group("quality").lower() if m.group("quality") else "unknown"
        }

    return {
        "valid": False,
        "reason": f"Could not parse filename: {filename}"
    }