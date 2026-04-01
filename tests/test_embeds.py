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


class TestImageEmbeds:
    def test_png_embed(self):
        article = render(_make_article("![[photo.png]]"))
        assert '<img src="/assets/photo.png" alt="photo.png">' in article.body_html

    def test_jpg_embed(self):
        article = render(_make_article("![[image.jpg]]"))
        assert '<img src="/assets/image.jpg" alt="image.jpg">' in article.body_html

    def test_svg_embed(self):
        article = render(_make_article("![[diagram.svg]]"))
        assert '<img src="/assets/diagram.svg" alt="diagram.svg">' in article.body_html

    def test_webp_embed(self):
        article = render(_make_article("![[photo.webp]]"))
        assert '<img src="/assets/photo.webp" alt="photo.webp">' in article.body_html

    def test_embed_with_base_url(self):
        article = render(_make_article("![[photo.png]]"), base_url="https://example.com")
        assert '<img src="https://example.com/assets/photo.png" alt="photo.png">' in article.body_html

    def test_non_image_embed_not_matched(self):
        article = render(_make_article("![[Some Note]]"))
        # Should NOT produce an img tag — non-image embeds are not handled
        assert "<img" not in article.body_html

    def test_embed_in_paragraph(self):
        article = render(_make_article("Here is an image: ![[photo.png]] in text."))
        assert '<img src="/assets/photo.png"' in article.body_html
        assert "Here is an image:" in article.body_html

    def test_multiple_embeds(self):
        article = render(_make_article("![[a.png]] and ![[b.jpg]]"))
        assert '<img src="/assets/a.png"' in article.body_html
        assert '<img src="/assets/b.jpg"' in article.body_html

    def test_embed_alongside_wikilink(self):
        path_map = {"some article": "/some-article/"}
        article = render(
            _make_article("![[photo.png]] and [[Some Article]]"),
            path_map=path_map,
        )
        assert '<img src="/assets/photo.png"' in article.body_html
        assert '<a href="/some-article/">Some Article</a>' in article.body_html
