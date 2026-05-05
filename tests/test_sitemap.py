import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.sitemap import generate_sitemap

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITE = SiteConfig(title="Test", base_url="https://example.com", description="D", author="A")


def _make_article(
    slug: str, tags: list[str] | None = None, is_home: bool = False, date: datetime | None = None
) -> Article:
    url_path = "/" if is_home else f"/{slug}/"
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title=slug,
        slug=slug,
        url_path=url_path,
        date=date or datetime(2026, 1, 15),
        body_markdown="",
        body_html="",
        is_home=is_home,
        tags=tags or [],
    )


def _locs(xml: str) -> list[str]:
    root = ET.fromstring(xml)
    return [el.text for el in root.findall(f".//{{{NS}}}loc")]


def _lastmods(xml: str) -> list[str]:
    root = ET.fromstring(xml)
    return [el.text for el in root.findall(f".//{{{NS}}}lastmod")]


class TestSitemapContent:
    def test_article_loc_uses_base_url(self):
        xml = generate_sitemap([_make_article("foo")], SITE)
        assert "https://example.com/foo/" in _locs(xml)

    def test_home_loc(self):
        xml = generate_sitemap([_make_article("home", is_home=True)], SITE)
        assert "https://example.com/" in _locs(xml)

    def test_all_pages_loc_always_present(self):
        xml = generate_sitemap([_make_article("foo")], SITE)
        assert "https://example.com/all/" in _locs(xml)

    def test_tag_page_loc(self):
        xml = generate_sitemap([_make_article("foo", tags=["python"])], SITE)
        assert "https://example.com/tags/python/" in _locs(xml)

    def test_multiple_tags(self):
        xml = generate_sitemap([_make_article("foo", tags=["python", "testing"])], SITE)
        locs = _locs(xml)
        assert "https://example.com/tags/python/" in locs
        assert "https://example.com/tags/testing/" in locs

    def test_lastmod_format_is_iso_date(self):
        xml = generate_sitemap([_make_article("foo", date=datetime(2026, 3, 15))], SITE)
        assert "2026-03-15" in _lastmods(xml)

    def test_lastmod_for_all_page_is_most_recent_article(self):
        articles = [
            _make_article("old", date=datetime(2025, 1, 1)),
            _make_article("new", date=datetime(2026, 6, 1)),
        ]
        xml = generate_sitemap(articles, SITE)
        root = ET.fromstring(xml)
        all_url = next(
            el for el in root.findall(f"{{{NS}}}url") if el.find(f"{{{NS}}}loc").text == "https://example.com/all/"
        )
        assert all_url.find(f"{{{NS}}}lastmod").text == "2026-06-01"

    def test_lastmod_for_tag_page_is_most_recent_in_tag(self):
        articles = [
            _make_article("old", tags=["python"], date=datetime(2025, 1, 1)),
            _make_article("new", tags=["python"], date=datetime(2026, 6, 1)),
        ]
        xml = generate_sitemap(articles, SITE)
        root = ET.fromstring(xml)
        tag_url = next(
            el
            for el in root.findall(f"{{{NS}}}url")
            if el.find(f"{{{NS}}}loc").text == "https://example.com/tags/python/"
        )
        assert tag_url.find(f"{{{NS}}}lastmod").text == "2026-06-01"


class TestSitemapStructure:
    def test_xml_namespace(self):
        xml = generate_sitemap([], SITE)
        assert NS in xml

    def test_xml_declaration(self):
        xml = generate_sitemap([], SITE)
        assert xml.startswith("<?xml")

    def test_empty_articles_produces_valid_xml(self):
        xml = generate_sitemap([], SITE)
        root = ET.fromstring(xml)
        assert root.tag == f"{{{NS}}}urlset"

    def test_empty_articles_has_all_pages_but_no_lastmod(self):
        xml = generate_sitemap([], SITE)
        root = ET.fromstring(xml)
        all_url = next(
            (el for el in root.findall(f"{{{NS}}}url") if el.find(f"{{{NS}}}loc").text == "https://example.com/all/"),
            None,
        )
        assert all_url is not None
        assert all_url.find(f"{{{NS}}}lastmod") is None

    def test_no_feed_or_robots_in_sitemap(self):
        xml = generate_sitemap([_make_article("foo")], SITE)
        locs = _locs(xml)
        assert not any("feed.xml" in _ for _ in locs)
        assert not any("robots.txt" in _ for _ in locs)


class TestSitemapWritten:
    def test_write_sitemap_creates_file(self, tmp_path):
        from paulblish.writer import write_sitemap

        articles = [_make_article("foo")]
        write_sitemap(articles, tmp_path, SITE)
        assert (tmp_path / "sitemap.xml").exists()

    def test_build_writes_sitemap(self, tmp_path):
        from pathlib import Path

        from click.testing import CliRunner

        from paulblish.cli import main

        fixtures = Path(__file__).parent / "fixtures"
        runner = CliRunner()
        runner.invoke(main, ["build", "-s", str(fixtures), "-o", str(tmp_path)])
        assert (tmp_path / "sitemap.xml").exists()
