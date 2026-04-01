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


class TestCallouts:
    def test_note_callout(self):
        md = "> [!NOTE]\n> This is a note."
        article = render(_make_article(md))
        assert 'class="callout callout-note"' in article.body_html
        assert 'data-callout="note"' in article.body_html
        assert "This is a note." in article.body_html

    def test_callout_title_rendered(self):
        md = "> [!WARNING]\n> Watch out."
        article = render(_make_article(md))
        assert '<div class="callout-title">Warning</div>' in article.body_html

    def test_callout_body_wrapper(self):
        md = "> [!TIP]\n> Here is a tip."
        article = render(_make_article(md))
        assert '<div class="callout-body">' in article.body_html
        assert "Here is a tip." in article.body_html

    def test_marker_not_in_body(self):
        md = "> [!NOTE]\n> Body text."
        article = render(_make_article(md))
        assert "[!NOTE]" not in article.body_html

    def test_case_insensitive_type(self):
        md = "> [!note]\n> Lowercase type."
        article = render(_make_article(md))
        assert 'class="callout callout-note"' in article.body_html

    def test_unknown_callout_type(self):
        md = "> [!CUSTOM]\n> Custom callout."
        article = render(_make_article(md))
        assert 'class="callout callout-custom"' in article.body_html
        assert "Custom callout." in article.body_html

    def test_regular_blockquote_unaffected(self):
        md = "> This is just a regular blockquote."
        article = render(_make_article(md))
        assert "<blockquote>" in article.body_html
        assert "callout" not in article.body_html

    def test_danger_callout(self):
        md = "> [!DANGER]\n> Dangerous!"
        article = render(_make_article(md))
        assert 'class="callout callout-danger"' in article.body_html
