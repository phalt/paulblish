"""Sitemap generation for Paulblish.

Generates a sitemap.xml listing all published article URLs, tag pages, and
the all-pages listing. Follows the Sitemaps protocol:
https://www.sitemaps.org/protocol.html
"""

import xml.etree.ElementTree as ET
from collections import defaultdict

from paulblish.models import Article, SiteConfig

NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _lastmod(articles: list[Article]) -> str | None:
    """Return YYYY-MM-DD of the most recent article date, or None if list is empty."""
    if not articles:
        return None
    return max(a.date for a in articles).strftime("%Y-%m-%d")


def generate_sitemap(articles: list[Article], site: SiteConfig) -> str:
    """Return a sitemap.xml string covering articles, tag pages, and /all/."""
    ET.register_namespace("", NAMESPACE)
    urlset = ET.Element(f"{{{NAMESPACE}}}urlset")

    def _add(loc: str, lastmod: str | None) -> None:
        url_el = ET.SubElement(urlset, f"{{{NAMESPACE}}}url")
        ET.SubElement(url_el, f"{{{NAMESPACE}}}loc").text = loc
        if lastmod:
            ET.SubElement(url_el, f"{{{NAMESPACE}}}lastmod").text = lastmod

    # Article and home pages
    for article in articles:
        loc = site.base_url + article.url_path
        _add(loc, article.date.strftime("%Y-%m-%d"))

    # /all/ listing
    non_home = [a for a in articles if not a.is_home]
    _add(site.base_url + "/all/", _lastmod(non_home))

    # /tags/{tag}/ pages
    tag_map: dict[str, list[Article]] = defaultdict(list)
    for article in non_home:
        for tag in article.tags:
            tag_map[tag].append(article)

    for tag, tagged in sorted(tag_map.items()):
        _add(site.base_url + f"/tags/{tag}/", _lastmod(tagged))

    ET.indent(urlset, space="  ")
    tree = ET.ElementTree(urlset)
    from io import StringIO

    buf = StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=True)
    return buf.getvalue() + "\n"
