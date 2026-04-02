"""Tests for RSS 2.0 feed generation (feed.py) and feed.xml output (writer.py)."""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from paulblish.feed import MAX_ITEMS, _plain_text_excerpt, _to_rfc822, generate_feed
from paulblish.models import Article, SiteConfig
from paulblish.writer import write, write_feed

SITE = SiteConfig(
    title="Test Blog",
    base_url="https://example.com",
    description="A test blog.",
    author="Tester",
)


def _make_article(
    slug: str,
    date: datetime,
    is_home: bool = False,
    description: str = "",
    body_html: str = "<p>Content.</p>",
    tags: list[str] | None = None,
) -> Article:
    url_path = "/" if is_home else f"/{slug}/"
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title=slug.replace("-", " ").title(),
        slug=slug,
        url_path=url_path,
        date=date,
        body_markdown="",
        body_html=body_html,
        description=description,
        is_home=is_home,
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# RFC 822 date formatting
# ---------------------------------------------------------------------------


class TestToRfc822:
    def test_format(self):
        dt = datetime(2026, 3, 15, 12, 0, 0)
        result = _to_rfc822(dt)
        assert result == "Sun, 15 Mar 2026 12:00:00 +0000"

    def test_single_digit_day_padded(self):
        dt = datetime(2026, 1, 5, 0, 0, 0)
        result = _to_rfc822(dt)
        assert "05 Jan 2026" in result


# ---------------------------------------------------------------------------
# Plain-text excerpt extraction
# ---------------------------------------------------------------------------


class TestPlainTextExcerpt:
    def test_strips_html_tags(self):
        result = _plain_text_excerpt("<p>Hello <strong>world</strong>.</p>")
        assert "<" not in result
        assert "Hello world" in result

    def test_short_text_returned_as_is(self):
        result = _plain_text_excerpt("<p>Short.</p>", max_length=200)
        assert result == "Short."

    def test_truncates_at_word_boundary(self):
        # Create content just over 20 chars
        result = _plain_text_excerpt("<p>one two three four five</p>", max_length=20)
        assert result.endswith("…")
        assert "<" not in result
        # Should not cut mid-word
        assert not result[:-1].endswith(" ")

    def test_collapses_whitespace(self):
        result = _plain_text_excerpt("<p>hello</p>  <p>world</p>")
        assert "  " not in result


# ---------------------------------------------------------------------------
# Feed XML structure
# ---------------------------------------------------------------------------


class TestGenerateFeed:
    def test_is_valid_xml(self):
        articles = [_make_article("post-one", datetime(2026, 3, 15))]
        xml_str = generate_feed(articles, SITE)
        # Should not raise
        ET.fromstring(xml_str)

    def test_rss_version(self):
        xml_str = generate_feed([], SITE)
        root = ET.fromstring(xml_str)
        assert root.tag == "rss"
        assert root.attrib["version"] == "2.0"

    def test_channel_title(self):
        xml_str = generate_feed([], SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/title").text == "Test Blog"

    def test_channel_link(self):
        xml_str = generate_feed([], SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/link").text == "https://example.com"

    def test_channel_description(self):
        xml_str = generate_feed([], SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/description").text == "A test blog."

    def test_item_count(self):
        articles = [_make_article(f"post-{i}", datetime(2026, 1, i + 1)) for i in range(5)]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        items = root.findall("channel/item")
        assert len(items) == 5

    def test_item_title(self):
        articles = [_make_article("my-post", datetime(2026, 3, 15))]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/item/title").text == "My Post"

    def test_item_link(self):
        articles = [_make_article("my-post", datetime(2026, 3, 15))]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/item/link").text == "https://example.com/my-post/"

    def test_item_guid(self):
        articles = [_make_article("my-post", datetime(2026, 3, 15))]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/item/guid").text == "https://example.com/my-post/"

    def test_item_pub_date_rfc822(self):
        articles = [_make_article("my-post", datetime(2026, 3, 15, 9, 0, 0))]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        pub_date = root.find("channel/item/pubDate").text
        assert "2026" in pub_date
        assert "+0000" in pub_date

    def test_items_sorted_newest_first(self):
        articles = [
            _make_article("old-post", datetime(2025, 1, 1)),
            _make_article("new-post", datetime(2026, 3, 15)),
            _make_article("mid-post", datetime(2025, 6, 1)),
        ]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        titles = [item.find("title").text for item in root.findall("channel/item")]
        assert titles == ["New Post", "Mid Post", "Old Post"]

    def test_home_article_excluded(self):
        articles = [
            _make_article("home", datetime(2026, 3, 15), is_home=True),
            _make_article("regular-post", datetime(2026, 3, 14)),
        ]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        items = root.findall("channel/item")
        assert len(items) == 1
        assert items[0].find("title").text == "Regular Post"

    def test_only_home_article_produces_empty_feed(self):
        articles = [_make_article("home", datetime(2026, 3, 15), is_home=True)]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        assert root.findall("channel/item") == []

    def test_item_count_capped_at_max(self):
        # Generate MAX_ITEMS + 5 articles; feed should cap at MAX_ITEMS
        from datetime import timedelta

        articles = [_make_article(f"post-{i}", datetime(2026, 1, 1) + timedelta(days=i)) for i in range(MAX_ITEMS + 5)]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        items = root.findall("channel/item")
        assert len(items) == MAX_ITEMS

    def test_capped_items_are_newest(self):
        # When capped, we should get the MAX_ITEMS newest
        from datetime import timedelta

        articles = [_make_article(f"post-{i}", datetime(2026, 1, 1) + timedelta(days=i)) for i in range(MAX_ITEMS + 5)]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        # First item should be the newest (post-24, assuming MAX_ITEMS=20 and 25 total)
        first_title = root.find("channel/item/title").text
        assert f"Post {MAX_ITEMS + 5 - 1}" in first_title  # "Post 24" or equivalent

    def test_item_description_uses_frontmatter(self):
        articles = [_make_article("post", datetime(2026, 3, 15), description="A great summary.")]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        desc = root.find("channel/item/description").text
        assert desc == "A great summary."

    def test_item_description_falls_back_to_excerpt(self):
        articles = [_make_article("post", datetime(2026, 3, 15), body_html="<p>This is the body text.</p>")]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        desc = root.find("channel/item/description").text
        assert "This is the body text." in desc
        assert "<" not in desc

    def test_last_build_date_present_when_articles_exist(self):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        xml_str = generate_feed(articles, SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/lastBuildDate") is not None

    def test_no_last_build_date_when_no_articles(self):
        xml_str = generate_feed([], SITE)
        root = ET.fromstring(xml_str)
        assert root.find("channel/lastBuildDate") is None

    def test_xml_declaration_present(self):
        xml_str = generate_feed([], SITE)
        assert xml_str.startswith("<?xml")


# ---------------------------------------------------------------------------
# write_feed integration
# ---------------------------------------------------------------------------


class TestWriteFeed:
    def test_writes_feed_xml(self, tmp_path):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        write_feed(articles, tmp_path, SITE)
        assert (tmp_path / "feed.xml").exists()

    def test_feed_xml_is_valid(self, tmp_path):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        write_feed(articles, tmp_path, SITE)
        content = (tmp_path / "feed.xml").read_text()
        ET.fromstring(content)  # should not raise

    def test_write_includes_feed_in_returned_paths(self, tmp_path):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        written = write(articles, tmp_path, site=SITE)
        assert any(p.name == "feed.xml" for p in written)


# ---------------------------------------------------------------------------
# Feed autodiscovery link in HTML output
# ---------------------------------------------------------------------------


class TestFeedDiscoveryLink:
    def test_base_template_includes_rss_link(self, tmp_path):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        write(articles, tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'type="application/rss+xml"' in html
        assert "feed.xml" in html

    def test_rss_link_points_to_correct_url(self, tmp_path):
        articles = [_make_article("post", datetime(2026, 3, 15))]
        write(articles, tmp_path, site=SITE)
        html = (tmp_path / "post" / "index.html").read_text()
        assert "https://example.com/feed.xml" in html
