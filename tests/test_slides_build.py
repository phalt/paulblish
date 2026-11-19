"""Slide decks end to end: config, scanning, vault lookups, rendering and the built site."""

import json
import re
import textwrap
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from paulblish.assets import AssetRef
from paulblish.cli import main
from paulblish.config import load_config
from paulblish.models import Deck, SiteConfig
from paulblish.scanner import scan
from paulblish.slides.build import (
    RUNTIME_DIR,
    AssetRegistry,
    DeckResolver,
    VaultIndex,
    find_slides_dir,
    render_deck,
    scan_decks,
)
from paulblish.slides.runtime import CDN, HIGHLIGHT_THEMES, MATHJAX_URL
from paulblish.templating import PELE_URL

FIXTURES = Path(__file__).parent / "fixtures"
SITE_TOML = '[site]\ntitle = "T"\nbase_url = "https://example.com"\ndescription = "D"\nauthor = "A"\n'


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"))
    return path


def _vault(tmp_path: Path, home_extra: str = "", slides_dir: str = "slides") -> Path:
    vault = tmp_path / "vault"
    _write(vault / "site.toml", SITE_TOML)
    _write(vault / "Home.md", f"---\npublish: true\nslug: home\n{home_extra}---\n\n# Home\n")
    _write(
        vault / "articles" / "post.md",
        "---\npublish: true\nslug: post\ntitle: Post\ndate: 2026-01-02\n---\n\nSee [[Talk]].\n",
    )
    _write(
        vault / slides_dir / "Talk.md",
        """
        ---
        publish: true
        date: 2026-02-03
        description: A talk
        ---

        # Hello

        Read [[Post]]

        ![[photo.png|200]]

        note: secret notes
        """,
    )
    (vault / "attachments").mkdir()
    (vault / "attachments" / "photo.png").write_bytes(b"\x89PNG fake")
    return vault


def _build(vault: Path, out: Path, *args: str):
    result = CliRunner().invoke(main, ["build", "-s", str(vault), "-o", str(out), *args])
    assert result.exit_code == 0, result.output
    return result


def _site() -> SiteConfig:
    return SiteConfig(title="T", base_url="https://example.com", description="D", author="A")


def _deck(path: Path, vault: Path) -> Deck:
    return Deck(
        source_path=path,
        relative_path=path.relative_to(vault),
        title=path.stem,
        slug=path.stem.lower(),
        url_path=f"/slides/{path.stem.lower()}/",
        date=datetime(2026, 1, 1),
        text=path.read_text(),
    )


# --- Config ------------------------------------------------------------------------------------


class TestConfig:
    def test_defaults(self, tmp_path):
        vault = tmp_path / "v"
        _write(vault / "site.toml", SITE_TOML)
        config, _ = load_config(vault)
        assert config.slides_directory == "slides"
        assert config.slides_css == []

    def test_home_frontmatter_applies_even_with_site_toml(self, tmp_path):
        vault = _vault(tmp_path, home_extra='slides_directory: "Talks"\nslides_css: "Talks/a.css, b.css"\n')
        config, source = load_config(vault)
        assert source == "site.toml"
        assert config.slides_directory == "Talks"
        assert config.slides_css == ["Talks/a.css", "b.css"]

    def test_slides_css_list(self, tmp_path):
        vault = _vault(tmp_path, home_extra="slides_css:\n  - one.css\n  - two.css\n")
        config, _ = load_config(vault)
        assert config.slides_css == ["one.css", "two.css"]


# --- Scanning ----------------------------------------------------------------------------------


class TestScanning:
    def test_find_slides_dir_is_case_insensitive(self, tmp_path):
        (tmp_path / "Slides").mkdir()
        assert find_slides_dir(tmp_path, "slides") == tmp_path / "Slides"
        assert find_slides_dir(tmp_path, "missing") is None

    def test_article_scan_skips_slides_dir(self, tmp_path):
        vault = _vault(tmp_path)
        articles, skipped = scan(vault, exclude_dir=vault / "slides")
        paths = {str(a.relative_path) for a in articles} | {str(s.path) for s in skipped}
        assert not any(p.startswith("slides") for p in paths)

    def test_scan_decks(self, tmp_path):
        vault = _vault(tmp_path, slides_dir="Slides")
        _write(vault / "Slides" / "Draft.md", "---\ntitle: Draft\n---\n# Draft\n")
        _write(vault / "Slides" / "custom.md", "---\npublish: true\nslug: My-Custom\n---\n# C\n")
        decks, skipped = scan_decks(vault / "Slides", vault)
        assert sorted((d.slug, d.url_path) for d in decks) == [
            ("my-custom", "/slides/my-custom/"),
            ("talk", "/slides/talk/"),
        ]
        assert [(str(s.path), s.reason) for s in skipped] == [("Slides/Draft.md", "publish is not true")]
        talk = next(d for d in decks if d.slug == "talk")
        assert talk.title == "Talk"
        assert talk.description == "A talk"
        assert talk.date == datetime(2026, 2, 3)

    def test_drafts_flag_includes_unpublished(self, tmp_path):
        vault = _vault(tmp_path)
        _write(vault / "slides" / "Draft.md", "# Draft\n")
        decks, _ = scan_decks(vault / "slides", vault, include_drafts=True)
        assert {d.slug for d in decks} == {"draft", "talk"}

    def test_duplicate_slug_skipped(self, tmp_path):
        vault = _vault(tmp_path)
        _write(vault / "slides" / "Other.md", "---\npublish: true\nslug: talk\n---\n# Other\n")
        decks, skipped = scan_decks(vault / "slides", vault)
        assert len(decks) == 1
        assert "duplicate deck slug 'talk'" in skipped[0].reason


# --- Vault lookups -----------------------------------------------------------------------------


class TestResolver:
    @pytest.fixture
    def setup(self, tmp_path):
        vault = _vault(tmp_path)
        _write(
            vault / "notes" / "Ref.md",
            """
            ---
            publish: false
            ---
            Intro

            # Part A
            Alpha

            ## Sub
            Beta

            # Part B
            Gamma

            A paragraph
            with a block ^blk
            """,
        )
        _write(vault / "slides" / "deck.css", ".x{}")
        deck = _deck(vault / "slides" / "Talk.md", vault)
        resolver = DeckResolver(
            deck=deck,
            index=VaultIndex(vault),
            registry=AssetRegistry([]),
            site=_site(),
            path_map={"post": "/articles/post/"},
        )
        return vault, resolver

    def test_find_file_deploys_to_assets(self, setup):
        _, resolver = setup
        assert resolver.find_file("photo.png") == "https://example.com/assets/photo.png"
        assert resolver.find_file("[[photo.png]]") == "https://example.com/assets/photo.png"
        assert [r.output_filename for r in resolver.registry.new_refs] == ["photo.png"]

    def test_missing_file_warns(self, setup):
        _, resolver = setup
        assert resolver.find_file("nope.png") is None
        assert "file not found: nope.png" in resolver.warnings[0]

    def test_asset_url_leaves_urls_alone(self, setup):
        _, resolver = setup
        assert resolver.asset_url("https://x.test/a.png") is None
        assert resolver.asset_url("attachments/photo.png") == "https://example.com/assets/photo.png"
        assert resolver.asset_url("https://example.com/assets/photo.png") is None

    def test_name_collision_with_article_asset_is_hashed(self, setup, tmp_path):
        vault, resolver = setup
        other = tmp_path / "elsewhere" / "photo.png"
        other.parent.mkdir()
        other.write_bytes(b"different")
        resolver.registry = AssetRegistry([AssetRef("photo.png", other, "photo.png")])
        url = resolver.find_file("attachments/photo.png")
        assert re.fullmatch(r"https://example.com/assets/[0-9a-f]{8}_photo\.png", url)
        # a file articles already publish keeps its name
        assert resolver.registry.add(other) == "photo.png"

    def test_parse_file_whole_note_drops_frontmatter(self, setup):
        _, resolver = setup
        content = resolver.parse_file("Ref.md", None)
        assert content.startswith("Intro")
        assert "publish" not in content

    def test_parse_file_heading_section(self, setup):
        _, resolver = setup
        section = resolver.parse_file("Ref.md", "Part A")
        assert section == "# Part A\nAlpha\n\n## Sub\nBeta\n\n\n"

    def test_parse_file_block(self, setup):
        _, resolver = setup
        assert resolver.parse_file("Ref.md", "^blk") == "A paragraph\nwith a block \n"

    def test_parse_file_missing_heading_keeps_embed(self, setup):
        _, resolver = setup
        assert resolver.parse_file("Ref.md", "Nope") == "![[Ref.md#Nope]]"

    def test_link_url(self, setup):
        _, resolver = setup
        assert resolver.link_url("Post") == "https://example.com/articles/post/"
        assert resolver.link_url("Post#Heading") == "https://example.com/articles/post/"
        assert resolver.link_url("Unknown") is None

    def test_stylesheets(self, setup):
        _, resolver = setup
        runtime = "https://example.com/static/reveal/"
        assert resolver.stylesheet("night", kind="theme") == runtime + "dist/theme/night.css"
        assert resolver.stylesheet("monokai", kind="highlight") == HIGHLIGHT_THEMES["monokai"].url
        assert resolver.stylesheet("css/vs2015.css", kind="highlight") == HIGHLIGHT_THEMES["vs2015"].url
        assert resolver.stylesheet("css/layout.css") == runtime + "css/layout.css"
        assert resolver.stylesheet("https://cdn.test/t.css", kind="theme") == "https://cdn.test/t.css"
        assert resolver.stylesheet("slides/deck.css") == "https://example.com/assets/deck.css"
        assert resolver.stylesheet("deck.css") == "https://example.com/assets/deck.css"


# --- Rendering ---------------------------------------------------------------------------------


def _render(tmp_path: Path, body: str, site: SiteConfig | None = None) -> tuple[Deck, list[str]]:
    vault = _vault(tmp_path)
    path = _write(vault / "slides" / "Case.md", body)
    deck = _deck(path, vault)
    warnings = render_deck(
        deck, site or _site(), VaultIndex(vault), AssetRegistry([]), {"post": "/articles/post/"}, PELE_URL
    )
    return deck, warnings


class TestRenderDeck:
    def test_page_loads_pinned_cdn_runtime_and_vendored_theme(self, tmp_path):
        deck, _ = _render(tmp_path, "---\ntheme: white\nhighlightTheme: monokai\n---\n# A\n")
        html = deck.html
        runtime = "https://example.com/static/reveal/"
        assert f'href="{runtime}dist/theme/white.css" id="theme"' in html
        assert f'href="{runtime}css/layout.css"' in html
        for key in ("reveal_css", "reveal_js", "markdown", "highlight", "zoom", "notes", "math", "chartjs", "chart"):
            file = CDN[key]
            assert f'"{file.url}" integrity="{file.integrity}" crossorigin="anonymous"' in html
        monokai = HIGHLIGHT_THEMES["monokai"]
        assert f'href="{monokai.url}" integrity="{monokai.integrity}"' in html
        assert f"mathjax: '{MATHJAX_URL}'" in html
        assert "app://obsidian.md" not in html

    def test_cdn_urls_are_pinned(self):
        for file in [*CDN.values(), *HIGHLIGHT_THEMES.values()]:
            assert re.match(r"https://cdn\.jsdelivr\.net/npm/(@[\w-]+/)?[\w.-]+@\d+\.\d+\.\d+/", file.url), file.url
            assert file.integrity.startswith("sha384-")
        assert "mathjax@3.2.0/" in MATHJAX_URL

    def test_reveal_options_from_frontmatter(self, tmp_path):
        deck, _ = _render(tmp_path, "---\ntransition: fade\nslideNumber: true\nwidth: 1280\n---\n# A\n")
        options = json.loads(
            re.search(r"var options = extend\(defaultOptions, (\{.*?\}), queryOptions\)", deck.html).group(1)
        )
        assert options["transition"] == "fade"
        assert options["slideNumber"] is True
        assert options["width"] == 1280
        assert options["height"] == 700

    def test_custom_controls_and_overview(self, tmp_path):
        default, _ = _render(tmp_path / "a", "# A\n")
        assert CDN["customcontrols_js"].url in default.html  # on by default upstream
        assert "toggle-overview" not in default.html
        overview, _ = _render(tmp_path / "b", "---\nenableOverview: true\n---\n# A\n")
        assert "toggle-overview" in overview.html
        off, _ = _render(tmp_path / "c", "---\nenableCustomControls: false\n---\n# A\n")
        assert CDN["customcontrols_js"].url not in off.html

    def test_dropped_plugins_are_ignored(self, tmp_path):
        deck, _ = _render(
            tmp_path,
            "---\nenableMenu: true\nenableChalkboard: true\nenablePointer: true\nenableTimeBar: true\n---\n# A\n",
        )
        for name in ("RevealMenu", "RevealChalkboard", "RevealPointer", "ElapsedTimeBar", "chalkboard", "menu.js"):
            assert name not in deck.html

    def test_slides_markup(self, tmp_path):
        deck, _ = _render(tmp_path, "# One\n\n---\n\n# Two\n\nnote: notes here\n")
        assert deck.html.count("data-markdown>") == 2
        assert '<aside class="notes"><p>notes here</p>' in deck.html

    def test_wikilinks_link_to_published_pages(self, tmp_path):
        deck, _ = _render(tmp_path, "See [[Post|the post]] and [[Missing]]\n")
        assert "[the post](https://example.com/articles/post/)" in deck.html
        assert "and Missing" in deck.html

    def test_images_become_asset_urls(self, tmp_path):
        deck, _ = _render(tmp_path, '![[photo.png|200]]\n\n<!-- slide bg="[[photo.png]]" -->\n')
        assert '<img src="https://example.com/assets/photo.png" alt=""' in deck.html
        assert 'data-background-image="https://example.com/assets/photo.png"' in deck.html

    def test_plain_bg_path_is_rewritten(self, tmp_path):
        deck, _ = _render(tmp_path, '<!-- slide bg="attachments/photo.png" -->\n# A\n')
        assert 'data-background-image="https://example.com/assets/photo.png"' in deck.html

    def test_site_slides_css_comes_after_deck_css(self, tmp_path):
        site = _site()
        site.slides_css = ["https://cdn.test/site.css"]
        deck, _ = _render(tmp_path, "---\ncss: https://cdn.test/deck.css\n---\n# A\n", site)
        assert deck.html.index("cdn.test/deck.css") < deck.html.index("cdn.test/site.css")

    def test_mermaid_uses_pele(self, tmp_path):
        deck, _ = _render(tmp_path, "```mermaid\nflowchart LR\n  A --> B\n```\n")
        assert PELE_URL in deck.html
        assert 'import { mount } from "' in deck.html
        assert "mermaid.min.js" not in deck.html
        assert "RevealMermaid" not in deck.html
        plain, _ = _render(tmp_path / "x", "# No diagrams\n")
        assert PELE_URL not in plain.html

    def test_title(self, tmp_path):
        deck, _ = _render(tmp_path, "# A\n")
        assert "<title>Case</title>" in deck.html
        titled, _ = _render(tmp_path / "t", "---\ntitle: My <Talk>\n---\n# A\n")
        assert "<title>My &lt;Talk&gt;</title>" in titled.html

    def test_missing_image_warns(self, tmp_path):
        _, warnings = _render(tmp_path, "![[ghost.png]]\n")
        assert any("ghost.png" in w for w in warnings)


# --- Full build --------------------------------------------------------------------------------


class TestBuild:
    def test_fixture_vault(self, tmp_path):
        out = tmp_path / "_site"
        result = _build(FIXTURES, out)
        assert "slides/demo-deck.md → /slides/demo-deck/ (slides)" in result.output
        assert "slides/draft-deck.md (publish is not true)" in result.output
        assert "slides/footer-template.md (publish is not true)" in result.output
        assert "1 slide deck," in result.output

        deck_html = (out / "slides" / "demo-deck" / "index.html").read_text()
        assert "dist/theme/night.css" in deck_html
        assert "https://example.com/assets/theme.css" in deck_html  # Home.md slides_css
        assert "https://example.com/simple-article/" in deck_html
        assert "https://example.com/assets/pb-logo.svg" in deck_html
        assert "Built with Paulblish" in deck_html  # template variable filled
        assert 'data-visibility="hidden"' in deck_html  # skip="true"
        assert (out / "assets" / "pb-logo.svg").is_file()
        assert (out / "assets" / "theme.css").is_file()
        assert (out / "static" / "reveal" / "dist" / "theme" / "night.css").is_file()
        assert (out / "static" / "reveal" / "css" / "layout.css").is_file()
        assert not (out / "static" / "reveal" / "plugin").exists()

        index = (out / "slides" / "index.html").read_text()
        assert 'href="https://example.com/slides/demo-deck/">Demo Deck</a>' in index
        assert "Every Advanced Slides feature" in index
        assert 'href="https://example.com/slides/">Slides</a>' in (out / "index.html").read_text()

    def test_decks_in_sitemap_but_not_feed_or_listings(self, tmp_path):
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        _build(vault, out)
        sitemap = (out / "sitemap.xml").read_text()
        assert "<loc>https://example.com/slides/</loc>" in sitemap
        assert "<loc>https://example.com/slides/talk/</loc>" in sitemap
        assert "/slides/talk/" not in (out / "feed.xml").read_text()
        assert "/slides/talk/" not in (out / "all" / "index.html").read_text()
        assert "/slides/talk/" not in (out / "articles" / "index.html").read_text()
        post = (out / "articles" / "post" / "index.html").read_text()
        assert "article-nav" not in post or "/slides/talk/" not in post.split("article-nav", 1)[1]

    def test_articles_can_link_to_decks(self, tmp_path):
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        _build(vault, out)
        post = (out / "articles" / "post" / "index.html").read_text()
        assert '<a href="https://example.com/slides/talk/">Talk</a>' in post

    def test_no_slides_dir(self, tmp_path):
        vault = _vault(tmp_path)
        for f in (vault / "slides").iterdir():
            f.unlink()
        (vault / "slides").rmdir()
        out = tmp_path / "_site"
        _build(vault, out)
        assert not (out / "slides").exists()
        assert not (out / "static" / "reveal").exists()
        assert ">Slides</a>" not in (out / "index.html").read_text()

    def test_unpublished_deck_is_removed_on_rebuild(self, tmp_path):
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        _build(vault, out)
        assert (out / "slides" / "talk" / "index.html").exists()
        talk = vault / "slides" / "Talk.md"
        talk.write_text(talk.read_text().replace("publish: true", "publish: false"))
        _build(vault, out, "--incremental")
        assert not (out / "slides").exists()
        assert not (out / "static" / "reveal").exists()

    def test_custom_slides_directory(self, tmp_path):
        vault = _vault(tmp_path, home_extra='slides_directory: "Talks"\n', slides_dir="Talks")
        out = tmp_path / "_site"
        result = _build(vault, out)
        assert "Talks/Talk.md → /talks/talk/ (slides)" in result.output
        assert (out / "talks" / "talk" / "index.html").is_file()
        assert (out / "talks" / "index.html").is_file()

    def test_capitalised_slides_dir_is_not_also_an_article(self, tmp_path):
        vault = _vault(tmp_path, slides_dir="Slides")
        out = tmp_path / "_site"
        result = _build(vault, out)
        assert "Slides/Talk.md → /slides/talk/ (slides)" in result.output
        assert result.output.count("Talk.md →") == 1
        assert "/slides/talk/" not in (out / "all" / "index.html").read_text()

    def test_custom_templates_without_slide_templates(self, tmp_path):
        import shutil

        from paulblish.writer import DEFAULT_TEMPLATES

        custom = tmp_path / "templates"
        shutil.copytree(DEFAULT_TEMPLATES, custom, ignore=shutil.ignore_patterns("reveal", "deck.html", "slides.html"))
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        _build(vault, out, "--templates", str(custom))
        assert (out / "slides" / "talk" / "index.html").is_file()
        assert "Talk" in (out / "slides" / "index.html").read_text()

    def test_broken_deck_does_not_stop_build(self, tmp_path):
        vault = _vault(tmp_path)
        _write(
            vault / "slides" / "Bad.md",
            "---\npublish: true\n---\n```chart\ntype: bar\nlabels: [a]\ntitle: x\ndata: [not json\n```\n",
        )
        out = tmp_path / "_site"
        result = _build(vault, out)
        assert "slides/Bad.md: deck not built" in result.output
        assert not (out / "slides" / "bad").exists()
        assert (out / "slides" / "talk" / "index.html").is_file()


def test_only_advanced_slides_build_output_is_vendored():
    files = sorted(p.relative_to(RUNTIME_DIR).as_posix() for p in RUNTIME_DIR.rglob("*") if p.is_file())
    themes = {"beige", "black", "blood", "consult", "league", "moon", "night", "serif", "simple", "sky", "solarized"}
    assert files == sorted(
        [
            "LICENSE-advanced-slides",
            "VENDOR.md",
            "css/layout.css",
            "dist/theme/fonts/league-gothic/league-gothic.css",
            *(f"dist/theme/{name}.css" for name in themes | {"white"}),
        ]
    )


def test_themes_load_source_sans_pro_from_pinned_cdn():
    for name in ("black", "white"):
        first = (RUNTIME_DIR / "dist" / "theme" / f"{name}.css").read_text().split("\n", 1)[0]
        assert first == (
            '@import "https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/theme/fonts/source-sans-pro/source-sans-pro.css";'
        )
