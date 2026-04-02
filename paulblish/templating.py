from collections import OrderedDict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from paulblish.models import Article, SiteConfig

DEFAULT_TEMPLATES = Path(__file__).parent.parent / "templates"


def _create_env(templates_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment with the given (or default) templates directory."""
    path = templates_dir if templates_dir else DEFAULT_TEMPLATES
    return Environment(loader=FileSystemLoader(str(path)), autoescape=False)


def render_article(article: Article, site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render a single article page. Uses home.html for the home article, article.html otherwise."""
    env = _create_env(templates_dir)
    template_name = "home.html" if article.is_home else "article.html"
    template = env.get_template(template_name)
    return template.render(article=article, site=site)


def render_tag_page(tag: str, articles: list[Article], site: SiteConfig, templates_dir: Path | None = None) -> str:
    """Render a tag listing page for a single tag."""
    env = _create_env(templates_dir)
    template = env.get_template("listing.html")
    sorted_articles = sorted(articles, key=lambda a: a.date, reverse=True)
    return template.render(title=f"#{tag}", articles=sorted_articles, site=site)


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

    return template.render(groups=groups, site=site)
