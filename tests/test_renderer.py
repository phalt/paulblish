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


class TestRenderBasicMarkdown:
    def test_bold(self):
        article = render(_make_article("**bold**"))
        assert "<strong>bold</strong>" in article.body_html

    def test_italic(self):
        article = render(_make_article("*italic*"))
        assert "<em>italic</em>" in article.body_html

    def test_heading(self):
        article = render(_make_article("## Section"))
        assert "<h2>Section</h2>" in article.body_html

    def test_link(self):
        article = render(_make_article("[click](https://example.com)"))
        assert '<a href="https://example.com">click</a>' in article.body_html

    def test_unordered_list(self):
        article = render(_make_article("- one\n- two\n"))
        assert "<ul>" in article.body_html
        assert "<li>one</li>" in article.body_html

    def test_paragraph(self):
        article = render(_make_article("Hello world"))
        assert "<p>Hello world</p>" in article.body_html

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        article = render(_make_article(md))
        assert "<table>" in article.body_html
        assert "<td>1</td>" in article.body_html


class TestRenderCodeBlocks:
    def test_fenced_code_with_language_uses_pygments(self):
        md = "```python\ndef hello():\n    pass\n```"
        article = render(_make_article(md))
        assert 'class="highlight"' in article.body_html
        # Pygments wraps tokens in spans
        assert "<span" in article.body_html

    def test_fenced_code_without_language_renders_plain(self):
        md = "```\nplain code\n```"
        article = render(_make_article(md))
        assert "<pre>" in article.body_html
        assert "<code>" in article.body_html
        assert "plain code" in article.body_html

    def test_unknown_language_falls_back_to_plain(self):
        md = "```notareallanguage\nsome code\n```"
        article = render(_make_article(md))
        assert "<pre>" in article.body_html
        assert "<code" in article.body_html
        # Should NOT have pygments highlight wrapper
        assert 'class="highlight"' not in article.body_html

    def test_pygments_uses_css_classes_not_inline_styles(self):
        md = "```python\nx = 1\n```"
        article = render(_make_article(md))
        assert "style=" not in article.body_html


class TestRenderReturnValue:
    def test_returns_same_article(self):
        article = _make_article("hello")
        result = render(article)
        assert result is article

    def test_populates_body_html(self):
        article = _make_article("hello")
        assert article.body_html == ""
        render(article)
        assert article.body_html != ""
