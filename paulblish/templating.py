from collections import OrderedDict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from paulblish.models import Article, SiteConfig

DEFAULT_TEMPLATES = Path(__file__).parent.parent / "templates"


def _create_env(templates_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment with the given (or default) templates directory."""
    path = templates_dir if templates_dir else DEFAULT_TEMPLATES
    env = Environment(loader=FileSystemLoader(str(path)), autoescape=False)
    env.filters["basename"] = lambda p: Path(p).name
    return env


def _og_context(site: SiteConfig, article: Article | None = None) -> dict:
    """Build the page_title, page_description, page_url context used by Open Graph / Twitter tags."""
    page_title = article.title if article else site.title
    page_description = (article.description if article and article.description else None) or site.description
    page_url = (site.base_url + article.url_path) if article else site.base_url
    return {
        "page_title": page_title,
        "page_description": page_description,
        "page_url": page_url,
    }


def render_article(article: Article, site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render a single article page. Uses home.html for the home article, article.html otherwise."""
    env = _create_env(templates_dir)
    template_name = "home.html" if article.is_home else "article.html"
    template = env.get_template(template_name)
    return template.render(article=article, site=site, **_og_context(site, article))


def render_tag_page(tag: str, articles: list[Article], site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render a tag listing page for a single tag."""
    env = _create_env(templates_dir)
    template = env.get_template("listing.html")
    sorted_articles = sorted(articles, key=lambda a: a.date, reverse=True)
    return template.render(title=f"#{tag}", articles=sorted_articles, site=site, **_og_context(site))


def render_404(site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render the 404 error page."""
    env = _create_env(templates_dir)
    template = env.get_template("404.html")
    return template.render(site=site, **_og_context(site))


def render_all_pages(articles: list[Article], site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render the all-pages listing, grouped by path_prefix, sorted by date descending."""
    env = _create_env(templates_dir)
    template = env.get_template("all_pages.html")

    # Group articles by path_prefix, sorted by date descending within each group
    groups: OrderedDict[str, list[Article]] = OrderedDict()
    for article in sorted(articles, key=lambda a: (a.path_prefix, a.date), reverse=False):
        prefix = article.path_prefix
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(article)

    # Sort within each group by date descending
    for prefix in groups:
        groups[prefix].sort(key=lambda a: a.date, reverse=True)

    return template.render(groups=groups, site=site, **_og_context(site))
