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


class TestFootnotes:
    def test_basic_footnote(self):
        md = "Here is a footnote[^1].\n\n[^1]: The footnote text."
        article = render(_make_article(md))
        assert "footnote" in article.body_html.lower()
        assert "The footnote text." in article.body_html

    def test_footnote_reference_link(self):
        md = "Text[^note].\n\n[^note]: Definition."
        article = render(_make_article(md))
        # Should render a superscript anchor back-reference
        assert "<sup" in article.body_html
        assert "Definition." in article.body_html

    def test_multiple_footnotes(self):
        md = "First[^1] and second[^2].\n\n[^1]: One.\n\n[^2]: Two."
        article = render(_make_article(md))
        assert "One." in article.body_html
        assert "Two." in article.body_html

    def test_no_footnote_syntax_unchanged(self):
        article = render(_make_article("Plain text with no footnotes."))
        assert "Plain text with no footnotes." in article.body_html
