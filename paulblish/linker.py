from paulblish.models import Article


def _normalise(name: str) -> str:
    """Normalise a note name for lookup: strip .md, lowercase, strip whitespace."""
    name = name.strip()
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name.lower()


def build_path_map(articles: list[Article]) -> dict[str, str]:
    """Build a lookup table mapping normalised note titles to their url_path."""
    path_map: dict[str, str] = {}
    for article in articles:
        key = _normalise(article.title)
        path_map[key] = article.url_path
    return path_map
