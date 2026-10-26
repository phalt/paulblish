from paulblish.models import Article


def _normalise(name: str) -> str:
    """Normalise a note name for lookup: strip .md, lowercase, strip whitespace."""
    name = name.strip()
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name.lower()


def build_path_map(articles: list[Article]) -> dict[str, str]:
    """Build a lookup table mapping normalised note names and titles to their url_path."""
    # Obsidian links by filename, so a filename beats another note's frontmatter title
    path_map = {_normalise(article.source_path.stem): article.url_path for article in articles}
    for article in articles:
        path_map.setdefault(_normalise(article.title), article.url_path)
    return path_map
