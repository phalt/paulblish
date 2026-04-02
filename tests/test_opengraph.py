"""Tests for Open Graph and Twitter Card meta tag injection (8.3)."""

from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.writer import write

SITE = SiteConfig(title="Test Blog", base_url="https://example.com", description="Site description.", author="Tester")
SITE_WITH_AVATAR = SiteConfig(
    title="Test Blog",
    base_url="https://example.com",
    description="Site description.",
    author="Tester",
    avatar="images/me.jpg",
)


def _make_article(
    slug: str,
    title: str = "My Post",
    description: str = "",
    is_home: bool = False,
) -> Article:
    url_path = "/" if is_home else f"/{slug}/"
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title=title,
        slug=slug,
        url_path=url_path,
        date=datetime(2026, 3, 15),
        body_markdown="",
        body_html="<p>Content.</p>",
        description=description,
        is_home=is_home,
    )


class TestOpenGraphArticle:
    def test_og_title_uses_article_title(self, tmp_path):
        article = _make_article("post", title="My Great Post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'property="og:title"' in html
        assert 'content="My Great Post"' in html

    def test_og_description_uses_article_description(self, tmp_path):
        article = _make_article("post", description="A specific summary.")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'content="A specific summary."' in html

    def test_og_description_falls_back_to_site_description(self, tmp_path):
        article = _make_article("post", description="")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'content="Site description."' in html

    def test_og_url_uses_article_url(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert 'property="og:url"' in html
        assert 'content="https://example.com/my-post/"' in html

    def test_og_type_is_article(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'property="og:type"' in html
        assert 'content="article"' in html

    def test_og_site_name(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'property="og:site_name"' in html
        assert 'content="Test Blog"' in html


class TestTwitterCard:
    def test_twitter_card_type(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'name="twitter:card"' in html
        assert 'content="summary"' in html

    def test_twitter_title(self, tmp_path):
        article = _make_article("post", title="My Post Title")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'name="twitter:title"' in html
        assert 'content="My Post Title"' in html

    def test_twitter_description(self, tmp_path):
        article = _make_article("post", description="Tweet this.")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'name="twitter:description"' in html
        assert 'content="Tweet this."' in html


class TestOGImage:
    def test_og_image_absent_without_avatar(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert "og:image" not in html
        assert "twitter:image" not in html

    def test_og_image_present_with_avatar(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE_WITH_AVATAR)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'property="og:image"' in html
        assert "me.jpg" in html

    def test_twitter_image_present_with_avatar(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE_WITH_AVATAR)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'name="twitter:image"' in html

    def test_og_image_uses_basename_only(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE_WITH_AVATAR)
        html = (tmp_path / "post" / "index.html").read_text()
        # Should use the basename, not the full path "images/me.jpg"
        assert "https://example.com/assets/me.jpg" in html


class TestOGListingPages:
    def test_listing_uses_site_title(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "all" / "index.html").read_text()
        assert 'content="Test Blog"' in html

    def test_listing_uses_site_description(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "all" / "index.html").read_text()
        assert 'content="Site description."' in html

    def test_listing_url_is_base_url(self, tmp_path):
        article = _make_article("post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "all" / "index.html").read_text()
        assert 'content="https://example.com"' in html
