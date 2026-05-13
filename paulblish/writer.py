import hashlib
import shutil
from pathlib import Path

from paulblish.feed import generate_feed
from paulblish.models import Article, SiteConfig
from paulblish.sitemap import generate_sitemap
from paulblish.templating import render_404, render_all_pages, render_article, render_section_listing, render_tag_page

DEFAULT_TEMPLATES = Path(__file__).parent.parent / "templates"

HASHED_STATIC_EXTENSIONS = {".css"}


def _hashed_static_files(static_src: Path) -> dict[str, str]:
    """Map static filenames to their content-hashed versions for cache busting."""
    mapping: dict[str, str] = {}
    if not static_src.is_dir():
        return mapping
    for path in static_src.iterdir():
        if path.is_file() and path.suffix in HASHED_STATIC_EXTENSIONS:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
            mapping[path.name] = f"{path.stem}.{digest}{path.suffix}"
    return mapping


def _copy_static_dir(static_src: Path, static_dst: Path, mapping: dict[str, str]) -> None:
    """Copy static_src into static_dst, renaming files in *mapping* to their hashed names."""
    if static_dst.exists():
        shutil.rmtree(static_dst)
    static_dst.mkdir(parents=True)
    for entry in static_src.iterdir():
        if entry.is_dir():
            shutil.copytree(entry, static_dst / entry.name)
        else:
            dest_name = mapping.get(entry.name, entry.name)
            shutil.copy2(entry, static_dst / dest_name)


def output_path(article: Article, output_dir: Path) -> Path:
    """Compute the output file path for an article."""
    if article.is_home:
        return output_dir / "index.html"
    if article.path_prefix:
        return output_dir / article.path_prefix / article.slug / "index.html"
    return output_dir / article.slug / "index.html"


def assign_prev_next(articles: list[Article]) -> None:
    """Set prev_article / next_article on each non-home article, ordered by date then url_path."""
    sequence = sorted(
        [a for a in articles if not a.is_home],
        key=lambda a: (a.date, a.url_path),
    )
    for i, article in enumerate(sequence):
        article.prev_article = sequence[i - 1] if i > 0 else None
        article.next_article = sequence[i + 1] if i < len(sequence) - 1 else None


def write(
    articles: list[Article],
    output_dir: Path,
    site: SiteConfig,
    templates_dir: Path | None = None,
    articles_to_write: list[Article] | None = None,
) -> list[Path]:
    """Write rendered articles to the output directory. Returns list of written file paths.

    If *articles_to_write* is provided (incremental builds), only those articles have
    their individual HTML written.  All articles are still used for shared pages
    (listings, feeds, sitemaps).  Prev/next assignment always uses the full list.
    """
    assign_prev_next(articles)
    latest_articles = sorted(
        [a for a in articles if not a.is_home],
        key=lambda a: a.date,
        reverse=True,
    )[:3]

    # Compute static-file hash mapping up-front so templates can reference the hashed names
    tpl_dir = templates_dir if templates_dir else DEFAULT_TEMPLATES
    static_src = tpl_dir / "static"
    static_files = _hashed_static_files(static_src)

    subset = articles if articles_to_write is None else articles_to_write

    written: list[Path] = []
    for article in subset:
        path = output_path(article, output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        la = latest_articles if article.is_home else None
        html = render_article(article, site, templates_dir=templates_dir, latest_articles=la, static_files=static_files)
        path.write_text(html)
        written.append(path)

    # Write all-pages listing
    all_pages_path = output_dir / "all" / "index.html"
    all_pages_path.parent.mkdir(parents=True, exist_ok=True)
    all_pages_html = render_all_pages(articles, site, templates_dir=templates_dir, static_files=static_files)
    all_pages_path.write_text(all_pages_html)
    written.append(all_pages_path)

    # Write tag pages
    written.extend(
        write_tag_pages(articles, output_dir, site, templates_dir=templates_dir, static_files=static_files)
    )

    # Write section listing pages (/articles/ and /tools/)
    written.extend(
        write_section_listings(articles, output_dir, site, templates_dir=templates_dir, static_files=static_files)
    )

    # Write RSS feed
    written.extend(write_feed(articles, output_dir, site))

    # Write sitemap
    written.extend(write_sitemap(articles, output_dir, site))

    # Write robots.txt
    written.append(write_robots(output_dir, site))

    # Write 404 page
    written.append(write_404(output_dir, site, templates_dir=templates_dir, static_files=static_files))

    # Copy static assets from templates, renaming hashed files to their cache-busted names
    if static_src.is_dir():
        _copy_static_dir(static_src, output_dir / "static", static_files)

    return written


def write_tag_pages(
    articles: list[Article],
    output_dir: Path,
    site: SiteConfig,
    templates_dir: Path | None = None,
    static_files: dict[str, str] | None = None,
) -> list[Path]:
    """Write a /tags/{tag}/index.html page for each unique tag. Returns written paths."""
    from collections import defaultdict

    tag_map: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        for tag in article.tags:
            tag_map[tag].append(article)

    written: list[Path] = []
    for tag, tagged_articles in sorted(tag_map.items()):
        path = output_dir / "tags" / tag / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        html = render_tag_page(tag, tagged_articles, site, templates_dir=templates_dir, static_files=static_files)
        path.write_text(html)
        written.append(path)

    return written


def write_section_listings(
    articles: list[Article],
    output_dir: Path,
    site: SiteConfig,
    templates_dir: Path | None = None,
    static_files: dict[str, str] | None = None,
) -> list[Path]:
    """Write /articles/index.html and /tools/index.html listing pages. Returns written paths."""
    written: list[Path] = []
    for section in ("articles", "tools"):
        section_articles = [
            a for a in articles if a.path_prefix == section or a.path_prefix.startswith(f"{section}/")
        ]
        path = output_dir / section / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        html = render_section_listing(
            section, section_articles, site, templates_dir=templates_dir, static_files=static_files
        )
        path.write_text(html)
        written.append(path)
    return written


def write_feed(articles: list[Article], output_dir: Path, site: SiteConfig) -> list[Path]:
    """Generate and write feed.xml to the output root. Returns a list with the written path."""
    feed_path = output_dir / "feed.xml"
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(generate_feed(articles, site), encoding="utf-8")
    return [feed_path]


def write_sitemap(articles: list[Article], output_dir: Path, site: SiteConfig) -> list[Path]:
    """Generate and write sitemap.xml to the output root. Returns a list with the written path."""
    path = output_dir / "sitemap.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_sitemap(articles, site), encoding="utf-8")
    return [path]


def write_404(
    output_dir: Path,
    site: SiteConfig,
    templates_dir: Path | None = None,
    static_files: dict[str, str] | None = None,
) -> Path:
    """Render and write 404.html to the output root. GitHub Pages serves this automatically."""
    path = output_dir / "404.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_404(site, templates_dir=templates_dir, static_files=static_files))
    return path


def write_robots(output_dir: Path, site: SiteConfig) -> Path:
    """Write robots.txt to the output root. Allows all crawlers and links to sitemap."""
    content = f"User-agent: *\nAllow: /\n\nSitemap: {site.base_url}/sitemap.xml\n"
    path = output_dir / "robots.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def write_build_meta(output_dir: Path, base_url: str) -> Path:
    """Write .pb-meta.json to the output dir so pb serve can rewrite base_url for local preview."""
    import json

    path = output_dir / ".pb-meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"base_url": base_url}))
    return path


def write_cname(output_dir: Path, cname: str) -> Path | None:
    """Write a CNAME file if cname is non-empty. Returns the path written, or None."""
    if not cname:
        return None
    path = output_dir / "CNAME"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cname)
    return path
