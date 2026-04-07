import re

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from paulblish.models import Article
from paulblish.plugins.callouts import callouts_plugin
from paulblish.plugins.embeds import embeds_plugin
from paulblish.plugins.highlights import highlights_plugin
from paulblish.plugins.wikilinks import wikilinks_plugin

_formatter = HtmlFormatter(cssclass="highlight", nowrap=False)
_formatter_linenos = HtmlFormatter(cssclass="highlight", nowrap=False, linenos="table")

_COPY_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    "</svg>"
)


def _parse_title(attrs: str) -> str | None:
    """Extract title="..." or title='...' from a fenced code info string."""
    m = re.search(r'title=["\']([^"\']+)["\']', attrs)
    return m.group(1) if m else None


def _code_header(label: str) -> str:
    return (
        '<div class="code-header">'
        f'<span class="code-lang">{label}</span>'
        f'<button class="code-copy-btn" aria-label="Copy code">{_COPY_ICON}</button>'
        "</div>"
    )


def _highlight(code: str, lang: str, _attrs: str) -> str:
    """Highlight callback for markdown-it-py fenced code blocks."""
    if lang == "mermaid":
        # Pass through as a bare <pre class="mermaid"> for mermaid.js to render client-side
        from markupsafe import escape

        return f'<pre class="mermaid">{escape(code)}</pre>'
    if not lang:
        return ""  # markdown-it-py falls back to default <pre><code> rendering
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return ""  # unknown language, fall back to default rendering

    attrs = _attrs or ""
    use_linenos = "linenos" in attrs
    title = _parse_title(attrs)
    label = title if title else lang
    formatter = _formatter_linenos if use_linenos else _formatter
    highlighted = highlight(code, lexer, formatter)
    return f'<div class="code-block" data-lang="{lang}">{_code_header(label)}{highlighted}</div>'


_md = MarkdownIt("commonmark", {"highlight": _highlight}).enable("table")
wikilinks_plugin(_md)
embeds_plugin(_md)
highlights_plugin(_md)
footnote_plugin(_md)
callouts_plugin(_md)


def render(article: Article, path_map: dict[str, str] | None = None, base_url: str = "") -> Article:
    """Render an article's body_markdown to body_html. Returns the article with body_html populated."""
    env: dict = {}
    if path_map:
        env["path_map"] = path_map
    if base_url:
        env["base_url"] = base_url
    article.body_html = _md.render(article.body_markdown, env)
    return article
