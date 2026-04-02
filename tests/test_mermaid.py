from datetime import datetime
from pathlib import Path

from paulblish.models import Article
from paulblish.renderer import render


def _make_article(body_markdown: str) -> Article:
    return Article(
        source_path=Path("/vault/test.md"),
        relative_path=Path("test.md"),
        path_prefix="",
        title="Test",
        slug="test",
        url_path="/test/",
        date=datetime(2026, 1, 1),
        body_markdown=body_markdown,
    )


MERMAID_BLOCK = "```mermaid\ngraph TD\n  A --> B\n```"


class TestMermaid:
    def test_mermaid_block_renders_pre_tag(self):
        article = render(_make_article(MERMAID_BLOCK))
        assert '<pre class="mermaid">' in article.body_html

    def test_mermaid_content_preserved(self):
        article = render(_make_article(MERMAID_BLOCK))
        assert "graph TD" in article.body_html
        # --> is HTML-escaped; mermaid.js reads from the DOM so this is correct
        assert "A --&gt; B" in article.body_html

    def test_mermaid_not_wrapped_in_code_tag(self):
        article = render(_make_article(MERMAID_BLOCK))
        # Should be a bare <pre class="mermaid">, not <pre><code class="language-mermaid">
        assert "language-mermaid" not in article.body_html

    def test_mermaid_content_is_escaped(self):
        article = render(_make_article("```mermaid\n<script>alert(1)</script>\n```"))
        assert "<script>" not in article.body_html
        assert "&lt;script&gt;" in article.body_html

    def test_non_mermaid_fenced_block_unaffected(self):
        article = render(_make_article("```python\nprint('hello')\n```"))
        assert 'class="mermaid"' not in article.body_html


class TestMermaidScriptInTemplate:
    """The mermaid CDN script should only appear in pages that have a mermaid diagram."""

    def _render_html(self, body_markdown: str) -> str:
        from paulblish.models import SiteConfig
        from paulblish.templating import render_article

        article = render(_make_article(body_markdown))
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")
        return render_article(article, site)

    def test_script_included_when_article_has_mermaid(self):
        html = self._render_html("```mermaid\ngraph TD\n  A --> B\n```")
        assert "mermaid" in html
        assert "cdn.jsdelivr.net" in html

    def test_script_omitted_when_no_mermaid(self):
        html = self._render_html("Just some **markdown**.")
        assert "cdn.jsdelivr.net" not in html

    def test_script_omitted_for_non_mermaid_code_block(self):
        html = self._render_html("```python\nprint('hello')\n```")
        assert "cdn.jsdelivr.net" not in html
