"""Tool widget CSS and the helper script. Browser behaviour (dragging, live readouts) isn't
testable from Python; open the tool_widgets.md fixture in a browser to check it by eye."""

import re
from datetime import datetime
from pathlib import Path

import frontmatter

from paulblish.models import Article, SiteConfig
from paulblish.renderer import render
from paulblish.templating import render_article

CSS = (Path(__file__).parent.parent / "templates" / "static" / "style.css").read_text()
FIXTURE = Path(__file__).parent / "fixtures" / "tool_widgets.md"
SITE = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")

WIDGET_CLASSES = ["row", "fields", "panel", "switch", "segmented", "knob", "gauge", "bars", "stats", "error", "live"]
# Classes the helper script reads rather than the stylesheet
SCRIPT_ONLY_CLASSES = {"live"}


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


def _page(body_markdown: str) -> str:
    return render_article(render(_make_article(body_markdown)), SITE)


def _fixture_html() -> str:
    return render(_make_article(frontmatter.load(str(FIXTURE)).content)).body_html


def _rules_for(selector_fragment: str) -> list[str]:
    """Selectors of every CSS rule whose selector contains *selector_fragment*."""
    css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    return [s.strip() for s in re.findall(r"([^{}]+)\{", css) if selector_fragment in s]


class TestWidgetCss:
    def test_braces_balance(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        assert css.count("{") == css.count("}")

    def test_every_widget_class_is_styled(self):
        for cls in set(WIDGET_CLASSES) - SCRIPT_ONLY_CLASSES:
            assert _rules_for(f".{cls}"), cls

    def test_widget_rules_are_scoped_to_embeds(self):
        # Bare class names like .row must never leak into article styling
        for cls in set(WIDGET_CLASSES) - SCRIPT_ONLY_CLASSES:
            for selector in _rules_for(f".{cls}"):
                for part in selector.split(","):
                    if f".{cls}" in part:
                        assert ".html-embed-body" in selector, selector

    def test_widget_rules_have_zero_specificity(self):
        # Each widget class must sit inside :where() so a tool's own <style> always wins
        for cls in set(WIDGET_CLASSES) - SCRIPT_ONLY_CLASSES:
            for selector in _rules_for(f".{cls}"):
                bare = re.sub(r":where\((?:[^()]|\([^()]*\))*\)", "", selector)
                assert f".{cls}" not in bare, selector

    def test_range_fill_reads_value_variable(self):
        assert "var(--value, 0) * 1%" in CSS

    def test_meter_states_are_coloured(self):
        for pseudo in ("optimum-value", "suboptimum-value", "even-less-good-value"):
            assert f"::-webkit-meter-{pseudo}" in CSS
        for pseudo in ("optimum", "sub-optimum", "sub-sub-optimum"):
            assert f":-moz-meter-{pseudo}" in CSS

    def test_vendor_pseudo_elements_are_not_grouped(self):
        # A browser drops a whole rule if any selector in it is unknown to it
        for selector in _rules_for("::-"):
            assert not ("-webkit-" in selector and "-moz-" in selector), selector


class TestToolsScript:
    def test_included_on_embed_pages(self):
        html = _page('```html embed\n<input type="range">\n```')
        assert "output.live" in html
        assert "input.knob" in html

    def test_included_on_home_page(self):
        article = _make_article('```html embed\n<input type="range" class="knob">\n```')
        article.is_home = True
        html = render_article(render(article), SITE)
        assert "Wiring for tool widgets" in html

    def test_included_once(self):
        assert _page("```html embed\n<p>hi</p>\n```").count("Wiring for tool widgets") == 1

    def test_not_included_without_embed(self):
        html = _page("Just words.\n\n```html\n<p>shown as code</p>\n```")
        assert "output.live" not in html

    def test_script_loads_nothing_external(self):
        html = _page("```html embed\n<p>hi</p>\n```")
        script = html[html.index("Wiring for tool widgets") :]
        script = script[: script.index("</script>")]
        assert "http" not in script


class TestWidgetFixture:
    def test_fixture_renders_every_widget(self):
        html = _fixture_html()
        for cls in WIDGET_CLASSES:
            assert re.search(rf'class="(?:[^"]* )?{cls}(?: [^"]*)?"', html), cls

    def test_fixture_uses_at_most_one_class_per_element(self):
        for value in re.findall(r'class="([^"]*)"', _fixture_html()):
            if not value.startswith(("html-embed", "code-", "highlight", "linenos")):
                assert len(value.split()) <= 1, value

    def test_every_embed_has_a_title(self):
        source = frontmatter.load(str(FIXTURE)).content
        embeds = re.findall(r"^```html embed(.*)$", source, flags=re.M)
        assert embeds
        assert all("title=" in attrs for attrs in embeds)

    def test_fixture_shows_source_for_each_widget(self):
        # Every live embed is paired with a plain ```html block showing what to write,
        # except the final "All together" demo
        source = frontmatter.load(str(FIXTURE)).content
        embeds = len(re.findall(r"^```html embed", source, flags=re.M))
        snippets = len(re.findall(r"^```html$", source, flags=re.M))
        assert snippets == embeds - 1
