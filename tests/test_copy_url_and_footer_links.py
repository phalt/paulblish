"""Tests for copy-URL button (8.x) and footer RSS/sitemap links."""

from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.writer import write

SITE = SiteConfig(title="Test Blog", base_url="https://example.com", description="Desc.", author="Tester")


def _make_article(slug: str, title: str = "My Post") -> Article:
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title=title,
        slug=slug,
        url_path=f"/{slug}/",
        date=datetime(2026, 3, 15),
        body_markdown="",
        body_html="<p>Content.</p>",
    )


class TestCopyUrlButton:
    def test_copy_button_present_in_article(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert "copy-url-btn" in html

    def test_copy_button_contains_article_url(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert "https://example.com/my-post/" in html

    def test_copy_button_has_title_attribute(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert "Copy URL to article" in html or "copy url to article" in html.lower()

    def test_copy_button_not_on_listing_page(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "all" / "index.html").read_text()
        assert "copy-url-btn" not in html


class TestFooterLinks:
    def test_footer_has_rss_link(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert 'href="https://example.com/feed.xml"' in html

    def test_footer_has_sitemap_link(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "my-post" / "index.html").read_text()
        assert 'href="https://example.com/sitemap.xml"' in html

    def test_footer_links_on_listing_page(self, tmp_path):
        article = _make_article("my-post")
        write([article], tmp_path, site=SITE)
        html = (tmp_path / "all" / "index.html").read_text()
        assert 'href="https://example.com/feed.xml"' in html
        assert 'href="https://example.com/sitemap.xml"' in html
