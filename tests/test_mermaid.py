from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.renderer import render
from paulblish.templating import PELE_URL, PELE_VERSION, render_article


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


MERMAID_BLOCK = "```mermaid\ngraph TD\n  A --> B\n```"


class TestMermaid:
    def test_mermaid_block_renders_pre_tag(self):
        article = render(_make_article(MERMAID_BLOCK))
        assert '<pre class="mermaid">' in article.body_html

    def test_mermaid_content_preserved(self):
        article = render(_make_article(MERMAID_BLOCK))
        assert "graph TD" in article.body_html
        # --> is HTML-escaped; Pele is handed the <pre>'s textContent, which decodes it
        assert "A --&gt; B" in article.body_html

    def test_mermaid_not_wrapped_in_code_tag(self):
        article = render(_make_article(MERMAID_BLOCK))
        # Should be a bare <pre class="mermaid">, not <pre><code class="language-mermaid">
        assert "language-mermaid" not in article.body_html

    def test_mermaid_content_is_escaped(self):
        article = render(_make_article("```mermaid\n<script>alert(1)</script>\n```"))
        assert "<script>" not in article.body_html
        assert "&lt;script&gt;" in article.body_html

    def test_non_mermaid_fenced_block_unaffected(self):
        article = render(_make_article("```python\nprint('hello')\n```"))
        assert 'class="mermaid"' not in article.body_html


class TestPeleScriptInTemplate:
    """The Pele script should only appear in pages that have a mermaid diagram."""

    def _render_html(self, body_markdown: str) -> str:
        article = render(_make_article(body_markdown))
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")
        return render_article(article, site)

    def test_script_included_when_article_has_mermaid(self):
        html = self._render_html(MERMAID_BLOCK)
        assert f'import {{ mount }} from "{PELE_URL}";' in html

    def test_script_pins_exact_pele_version(self):
        assert f"pele@{PELE_VERSION}/" in PELE_URL
        assert PELE_VERSION.count(".") == 2

    def test_script_mounts_every_mermaid_block(self):
        html = self._render_html(MERMAID_BLOCK)
        assert 'document.querySelectorAll("pre.mermaid")' in html
        assert "mount(diagram, source.textContent)" in html

    def test_mermaid_js_no_longer_loaded(self):
        html = self._render_html(MERMAID_BLOCK)
        assert "mermaid.esm" not in html
        assert "npm/mermaid@" not in html

    def test_script_omitted_when_no_mermaid(self):
        html = self._render_html("Just some **markdown**.")
        assert PELE_URL not in html
        assert "cdn.jsdelivr.net" not in html

    def test_script_omitted_for_non_mermaid_code_block(self):
        html = self._render_html("```python\nprint('hello')\n```")
        assert "cdn.jsdelivr.net" not in html

    def test_pele_url_available_to_custom_templates(self, tmp_path: Path):
        (tmp_path / "article.html").write_text("{{ pele_url }}")
        article = render(_make_article(MERMAID_BLOCK))
        site = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")
        assert render_article(article, site, templates_dir=tmp_path) == PELE_URL


class TestPeleTheme:
    """Diagrams are themed from the site palette via Pele's CSS variables."""

    CSS = (Path(__file__).parent.parent / "templates" / "static" / "style.css").read_text()

    def test_diagram_container_maps_pele_variables(self):
        assert ".diagram {" in self.CSS
        for var in ("--pele-bg", "--pele-fg", "--pele-line", "--pele-surface", "--pele-border", "--pele-font"):
            assert f"{var}: var(--" in self.CSS, var

    def test_zoom_controls_moved_off_the_diagram(self):
        # Pele's default top-right column of zoom buttons covers the end of wide LR flowcharts.
        assert "--pele-zoom-top: auto;" in self.CSS
        assert "--pele-zoom-bottom: 0;" in self.CSS
        assert ".diagram:has(.pele-zoom)" in self.CSS
