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
