from pathlib import Path

from paulblish.models import Article


def _output_path(article: Article, output_dir: Path) -> Path:
    """Compute the output file path for an article."""
    if article.is_home:
        return output_dir / "index.html"
    if article.path_prefix:
        return output_dir / article.path_prefix / article.slug / "index.html"
    return output_dir / article.slug / "index.html"


def _wrap_html(article: Article) -> str:
    """Wrap rendered HTML in a minimal valid HTML document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{article.title}</title>
</head>
<body>
<div class="article-body">
{article.body_html}
</div>
</body>
</html>
"""


def write(articles: list[Article], output_dir: Path) -> list[Path]:
    """Write rendered articles to the output directory. Returns list of written file paths."""
    written: list[Path] = []
    for article in articles:
        path = _output_path(article, output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_wrap_html(article))
        written.append(path)
    return written
