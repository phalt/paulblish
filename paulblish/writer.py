import shutil
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.templating import render_all_pages, render_article

DEFAULT_TEMPLATES = Path(__file__).parent.parent / "templates"


def _output_path(article: Article, output_dir: Path) -> Path:
    """Compute the output file path for an article."""
    if article.is_home:
        return output_dir / "index.html"
    if article.path_prefix:
        return output_dir / article.path_prefix / article.slug / "index.html"
    return output_dir / article.slug / "index.html"


def write(
    articles: list[Article],
    output_dir: Path,
    site: SiteConfig,
    templates_dir: Path | None = None,
) -> list[Path]:
    """Write rendered articles to the output directory. Returns list of written file paths."""
    written: list[Path] = []
    for article in articles:
        path = _output_path(article, output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        html = render_article(article, site, templates_dir=templates_dir)
        path.write_text(html)
        written.append(path)

    # Write all-pages listing
    all_pages_path = output_dir / "all" / "index.html"
    all_pages_path.parent.mkdir(parents=True, exist_ok=True)
    all_pages_html = render_all_pages(articles, site, templates_dir=templates_dir)
    all_pages_path.write_text(all_pages_html)
    written.append(all_pages_path)

    # Copy static assets from templates
    tpl_dir = templates_dir if templates_dir else DEFAULT_TEMPLATES
    static_src = tpl_dir / "static"
    if static_src.is_dir():
        static_dst = output_dir / "static"
        if static_dst.exists():
            shutil.rmtree(static_dst)
        shutil.copytree(static_src, static_dst)

    return written


def write_cname(output_dir: Path, cname: str) -> Path | None:
    """Write a CNAME file if cname is non-empty. Returns the path written, or None."""
    if not cname:
        return None
    path = output_dir / "CNAME"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cname)
    return path
