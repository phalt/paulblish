"""Tests for emoji favicon support."""

from datetime import datetime
from pathlib import Path

from paulblish.config import load_config
from paulblish.models import Article, SiteConfig
from paulblish.writer import write


def _make_article(slug: str = "post", is_home: bool = False) -> Article:
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title="A Post",
        slug=slug,
        url_path="/" if is_home else f"/{slug}/",
        date=datetime(2026, 3, 15),
        body_markdown="",
        body_html="<p>Content.</p>",
        is_home=is_home,
    )


class TestEmojiFaviconConfig:
    def test_emoji_favicon_defaults_to_empty(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.emoji_favicon == ""

    def test_emoji_favicon_loaded_from_toml(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\nemoji_favicon = "🚀"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.emoji_favicon == "🚀"

    def test_emoji_favicon_loaded_from_home_md(self, tmp_path):
        (tmp_path / "Home.md").write_text(
            "---\n"
            "publish: true\n"
            'title: "T"\nbase_url: "http://x"\ndescription: "D"\nauthor: "A"\n'
            'emoji_favicon: "🦊"\n'
            "---\n\n# Hi\n"
        )
        config, _ = load_config(tmp_path)
        assert config.emoji_favicon == "🦊"


class TestEmojiFaviconRendering:
    def test_favicon_link_emitted_when_set(self, tmp_path):
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A", emoji_favicon="🚀")
        write([_make_article(is_home=True)], tmp_path, site=site)
        html = (tmp_path / "index.html").read_text()
        assert 'rel="icon"' in html
        assert "data:image/svg+xml" in html
        assert "🚀" in html

    def test_favicon_link_absent_when_unset(self, tmp_path):
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")
        write([_make_article(is_home=True)], tmp_path, site=site)
        html = (tmp_path / "index.html").read_text()
        assert 'rel="icon"' not in html

    def test_favicon_link_present_on_article_pages(self, tmp_path):
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A", emoji_favicon="🦊")
        write([_make_article("post")], tmp_path, site=site)
        html = (tmp_path / "post" / "index.html").read_text()
        assert 'rel="icon"' in html
        assert "🦊" in html
