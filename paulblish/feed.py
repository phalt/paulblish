"""RSS 2.0 feed generation for Paulblish.

Generates a feed.xml from published articles (excluding the Home page),
sorted by date descending, capped at 20 items.
"""

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from paulblish.models import Article, SiteConfig

MAX_ITEMS = 20
EXCERPT_LENGTH = 200  # characters of plain text used as description fallback


def _to_rfc822(dt: datetime) -> str:
    """Format a datetime as RFC 822, as required by RSS 2.0.

    Example: Mon, 15 Mar 2026 00:00:00 +0000
    """
    # Ensure we always emit UTC offset regardless of whether dt is tz-aware.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _plain_text_excerpt(html: str, max_length: int = EXCERPT_LENGTH) -> str:
    """Strip HTML tags from body_html and return a truncated plain-text excerpt.

    Used as the RSS <description> fallback when article.description is empty.
    Strips tags, collapses whitespace, and truncates at word boundary.
    """
    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    # Truncate at last word boundary before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"


def _item_description(article: Article) -> str:
    """Return the RSS item description: frontmatter description or plain-text excerpt."""
    if article.description:
        return article.description
    return _plain_text_excerpt(article.body_html)


def generate_feed(articles: list[Article], site: SiteConfig) -> str:
    """Generate an RSS 2.0 feed from published articles.

    Excludes the Home article, sorts by date descending, caps at MAX_ITEMS.
    Returns the feed as an XML string (UTF-8, with XML declaration).
    """
    # Exclude home, sort newest first, cap at MAX_ITEMS
    feed_articles = sorted(
        [a for a in articles if not a.is_home],
        key=lambda a: a.date,
        reverse=True,
    )[:MAX_ITEMS]

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = site.title
    ET.SubElement(channel, "link").text = site.base_url
    ET.SubElement(channel, "description").text = site.description

    if feed_articles:
        ET.SubElement(channel, "lastBuildDate").text = _to_rfc822(feed_articles[0].date)

    for article in feed_articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article.title
        ET.SubElement(item, "link").text = site.base_url + article.url_path
        ET.SubElement(item, "guid").text = site.base_url + article.url_path
        ET.SubElement(item, "pubDate").text = _to_rfc822(article.date)
        ET.SubElement(item, "description").text = _item_description(article)

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")

    import io

    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")
