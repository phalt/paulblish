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


class TestHighlights:
    def test_basic_highlight(self):
        article = render(_make_article("This is ==highlighted== text."))
        assert "<mark>highlighted</mark>" in article.body_html

    def test_highlight_in_sentence(self):
        article = render(_make_article("Before ==the mark== after."))
        assert "<mark>the mark</mark>" in article.body_html
        assert "Before" in article.body_html
        assert "after" in article.body_html

    def test_multiple_highlights(self):
        article = render(_make_article("==one== and ==two=="))
        assert "<mark>one</mark>" in article.body_html
        assert "<mark>two</mark>" in article.body_html

    def test_unclosed_highlight_not_rendered(self):
        article = render(_make_article("This is ==not closed"))
        assert "<mark>" not in article.body_html

    def test_highlight_not_confused_with_code(self):
        article = render(_make_article("`code` and ==mark=="))
        assert "<code>code</code>" in article.body_html
        assert "<mark>mark</mark>" in article.body_html
