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


EMBED_BLOCK = '```html embed\n<form id="test"><button>Go</button></form>\n<script>console.log("ok")</script>\n```'

PLAIN_HTML_BLOCK = "```html\n<form id=\"test\"><button>Go</button></form>\n```"


class TestHtmlEmbed:
    def test_embed_block_renders_raw_html(self):
        article = render(_make_article(EMBED_BLOCK))
        assert '<form id="test">' in article.body_html

    def test_embed_block_wrapped_in_div(self):
        article = render(_make_article(EMBED_BLOCK))
        assert 'class="html-embed"' in article.body_html

    def test_embed_block_preserves_script_tags(self):
        article = render(_make_article(EMBED_BLOCK))
        assert "<script>" in article.body_html

    def test_embed_block_does_not_escape_html(self):
        article = render(_make_article(EMBED_BLOCK))
        # Raw HTML — angle brackets must NOT be entity-encoded
        assert "&lt;form" not in article.body_html
        assert "&lt;script&gt;" not in article.body_html

    def test_plain_html_block_is_still_highlighted(self):
        # ```html without "embed" must still be syntax-highlighted code, not raw injection
        article = render(_make_article(PLAIN_HTML_BLOCK))
        assert 'class="html-embed"' not in article.body_html

    def test_embed_keyword_in_attrs_triggers_embed(self):
        block = '```html embed title="My tool"\n<p>hello</p>\n```'
        article = render(_make_article(block))
        assert "<p>hello</p>" in article.body_html
        assert 'class="html-embed"' in article.body_html

    def test_embed_block_does_not_load_external_resources(self):
        # Embedding HTML should not inject any CDN scripts from paulblish itself
        from paulblish.models import SiteConfig
        from paulblish.templating import render_article

        article = render(_make_article(EMBED_BLOCK))
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")
        html = render_article(article, site)
        # The mermaid CDN script must not appear for non-mermaid pages
        assert "mermaid" not in html or "cdn.jsdelivr.net" not in html

    def test_air_fryer_fixture_renders(self):
        """End-to-end: the air fryer converter fixture renders with a working form."""
        fixture = Path(__file__).parent / "fixtures" / "air_fryer_converter.md"
        import frontmatter

        post = frontmatter.load(str(fixture))
        article = _make_article(post.content)
        article = render(article)
        assert 'class="html-embed"' in article.body_html
        assert "af-form" in article.body_html
        assert "afConvert" in article.body_html
        assert "<style>" in article.body_html
