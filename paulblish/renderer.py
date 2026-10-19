import re
from collections.abc import Sequence

from markdown_it import MarkdownIt
from markdown_it.common.utils import unescapeAll
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict
from markupsafe import escape
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


_EMBED_KEYWORDS = frozenset({"embed", "embedded"})


def _is_embed(lang: str, attrs: str) -> bool:
    """True for ```html embed (and ```html embedded, the spelling used in older docs)."""
    return lang == "html" and not _EMBED_KEYWORDS.isdisjoint(attrs.split())


def _html_embed(code: str, attrs: str) -> str:
    """Wrap author HTML in the sketch-pad container. The code itself is passed through raw."""
    label = escape(_parse_title(attrs) or "Tool")
    return (
        '<div class="html-embed">'
        f'<div class="html-embed-bar"><span class="html-embed-label">{label}</span></div>'
        f'<div class="html-embed-body">{code}</div>'
        "</div>"
    )


def _highlight(code: str, lang: str, attrs: str) -> str:
    """Render a fenced block to finished HTML, or return "" to use markdown-it-py's default <pre><code>."""
    if lang == "mermaid":
        # Bare <pre class="mermaid"> for mermaid.js to render client-side
        return f'<pre class="mermaid">{escape(code)}</pre>'
    if _is_embed(lang, attrs):
        # Raw HTML pass-through: the author opted in explicitly via "embed"
        return _html_embed(code, attrs)
    if not lang:
        return ""
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return ""

    title = _parse_title(attrs)
    label = title if title else lang
    formatter = _formatter_linenos if "linenos" in attrs else _formatter
    highlighted = highlight(code, lexer, formatter)
    return f'<div class="code-block" data-lang="{lang}">{_code_header(label)}{highlighted}</div>'


def _render_fence(self: RendererHTML, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType) -> str:
    """Fence rule that returns our blocks as-is.

    markdown-it-py's own fence rule only skips its <pre><code> wrapper when highlight output
    starts with "<pre", so <div class="html-embed"> and <div class="code-block"> were being
    nested inside <pre><code>. Owning the rule avoids that.
    """
    token = tokens[idx]
    lang, _, attrs = unescapeAll(token.info).strip().partition(" ")
    if rendered := _highlight(token.content, lang, attrs):
        return rendered + "\n"
    return self.fence(tokens, idx, options, env)


_md = MarkdownIt("commonmark").enable("table")
_md.add_render_rule("fence", _render_fence)
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
