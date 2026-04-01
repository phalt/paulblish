from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from paulblish.models import Article
from paulblish.plugins.wikilinks import wikilinks_plugin

_formatter = HtmlFormatter(cssclass="highlight", nowrap=False)


def _highlight(code: str, lang: str, _attrs: str) -> str:
    """Highlight callback for markdown-it-py fenced code blocks."""
    if not lang:
        return ""  # markdown-it-py falls back to default <pre><code> rendering
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return ""  # unknown language, fall back to default rendering
    return highlight(code, lexer, _formatter)


_md = MarkdownIt("commonmark", {"highlight": _highlight}).enable("table")
wikilinks_plugin(_md)


def render(article: Article, path_map: dict[str, str] | None = None) -> Article:
    """Render an article's body_markdown to body_html. Returns the article with body_html populated."""
    env = {"path_map": path_map} if path_map else {}
    article.body_html = _md.render(article.body_markdown, env)
    return article
