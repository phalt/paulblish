"""CV pages: parsing, column routing, the web page, the PDF, and pb build / pb pdf end to end."""

import os
import shutil
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from paulblish.cli import main
from paulblish.cv.build import (
    DEFAULT_TEMPLATES,
    NotACVError,
    _weasyprint_html,
    load_cv,
    render_cv,
    render_cv_page,
    render_print_html,
    split_sections,
    write_pdf,
)
from paulblish.models import SiteConfig
from paulblish.scanner import scan

FIXTURES = Path(__file__).parent / "fixtures"
CV_MD = FIXTURES / "cv" / "cv.md"
BESPOKE_MD = FIXTURES / "cv" / "cv-bespoke.md"
PHONE = "+44 7745 804293"
SITE = SiteConfig(title="T", base_url="https://example.com", description="D", author="A")


def _cv(path: Path = CV_MD, **overrides):
    cv = load_cv(path, url_path="/cv/", slug="cv")
    for key, value in overrides.items():
        setattr(cv, key, value)
    return cv


def _cv_text(tmp_path: Path, body: str, frontmatter: str = "") -> Path:
    path = tmp_path / "doc.md"
    path.write_text(f"---\nlayout: cv\ntitle: Ada Lovelace\n{frontmatter}---\n\n" + textwrap.dedent(body).lstrip())
    return path


def _vault(tmp_path: Path, cv_source: Path = CV_MD) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    shutil.copy(FIXTURES / "site.toml", vault / "site.toml")
    (vault / "Home.md").write_text("---\npublish: true\nslug: home\n---\n\nSee [[cv]].\n")
    (vault / "post.md").write_text("---\npublish: true\nslug: post\ntitle: Post\ntags: [a]\n---\n\nHello.\n")
    shutil.copy(cv_source, vault / "cv.md")
    return vault


def _invoke(*args: str, exit_code: int = 0):
    result = CliRunner().invoke(main, list(args))
    assert result.exit_code == exit_code, result.output
    return result


def _build(vault: Path, out: Path, *args: str):
    return _invoke("build", "-s", str(vault), "-o", str(out), *args)


class TestLoad:
    def test_scanner_records_layout(self, tmp_path):
        vault = _vault(tmp_path)
        (vault / "post.md").write_text("---\npublish: true\nslug: post\nlayout: ' CV '\n---\n")
        articles, _ = scan(vault)
        assert {a.slug: a.layout for a in articles} == {"home": "", "post": "cv", "cv": "cv"}

    def test_frontmatter_fields(self):
        cv = load_cv(CV_MD)
        assert cv.title == "Paul Hallett"
        assert cv.tagline.startswith("Engineering leader")
        assert (cv.location, cv.email, cv.phone, cv.github, cv.website) == (
            "Norwich, UK",
            "case@hey.com",
            PHONE,
            "github.com/phalt",
            "",
        )
        assert cv.sidebar == ["Education", "Skills", "Technologies", "Awards", "Languages", "Values", "Hobbies"]
        assert cv.relative_path == Path("cv.md")

    def test_default_pdf_name_dashes_the_title(self, tmp_path):
        assert load_cv(CV_MD).pdf_name == "Paul-Hallett-CV.pdf"
        path = _cv_text(tmp_path, "Hi\n", "title: ' Ada   King Lovelace '\n")
        assert load_cv(path).pdf_name == "Ada-King-Lovelace-CV.pdf"

    def test_pdf_name_cannot_leave_the_cv_directory(self, tmp_path):
        path = _cv_text(tmp_path, "Hi\n", "pdf_name: ../../ada.pdf\n")
        assert load_cv(path).pdf_name == "ada.pdf"

    def test_ignores_publish(self):
        assert load_cv(BESPOKE_MD).title == "Paul Hallett"

    def test_rejects_a_file_without_layout_cv(self):
        with pytest.raises(NotACVError, match="layout: cv"):
            load_cv(FIXTURES / "simple_article.md")


class TestSplitSections:
    def test_intro_and_sections_in_source_order(self):
        intro, sections = split_sections(load_cv(CV_MD).body_markdown)
        assert intro.strip().startswith("I lead the team behind Kraken Phone")
        assert "##" not in intro
        assert [name for name, _ in sections] == [
            "Experience",
            "Open source",
            "Education",
            "Skills",
            "Technologies",
            "Awards",
            "Languages",
            "Values",
            "Hobbies",
        ]
        assert sections[0][1].startswith("## Experience\n")
        assert "### Twilio" in sections[0][1]

    def test_heading_inside_a_code_fence_does_not_split(self):
        intro, sections = split_sections("Intro\n\n## Notes\n\n```md\n## Not a section\n```\n\n## Skills\n\nAll\n")
        assert intro == "Intro\n"
        assert [name for name, _ in sections] == ["Notes", "Skills"]
        assert "## Not a section" in sections[0][1]

    def test_no_sections_is_all_intro(self):
        assert split_sections("Just me.\n\n### Not h2\n") == ("Just me.\n\n### Not h2\n", [])


class TestRenderCV:
    def test_sidebar_sections_go_right_in_source_order(self):
        cv = _cv()
        assert render_cv(cv) == []
        side = cv.side_html
        names = ["EDUCATION", "SKILLS", "TECHNOLOGIES", "AWARDS", "LANGUAGES", "VALUES", "HOBBIES"]
        positions = [side.upper().index(f"<H2>{name}</H2>") for name in names]
        assert positions == sorted(positions)
        assert "<h2>Experience</h2>" in cv.main_html and "<h2>Open source</h2>" in cv.main_html
        assert "<h2>Experience</h2>" not in side
        assert "<code>Python</code>" in side
        assert cv.intro_html.startswith("<p>I lead the team")

    def test_sidebar_names_match_case_insensitively(self):
        cv = _cv(sidebar=["education", "SKILLS"])
        assert render_cv(cv) == []
        assert "<h2>Education</h2>" in cv.side_html and "<h2>Skills</h2>" in cv.side_html
        assert "<h2>Technologies</h2>" in cv.main_html

    def test_unknown_sidebar_name_warns(self):
        cv = _cv(sidebar=["Skills", "Hobbys"])
        assert render_cv(cv) == ["cv.md: sidebar section 'Hobbys' matches no section"]

    def test_role_heading_and_hard_breaks(self):
        cv = _cv()
        render_cv(cv)
        assert "<h3>Kraken Tech — <em>Lead Software Engineer, Kraken Phone</em></h3>\n<p>London UK" in cv.main_html
        assert "2019 – 2020<br />" in cv.main_html
        assert "<strong>University of Plymouth</strong><br />" in cv.side_html

    def test_wikilinks_without_a_path_map_are_plain_text(self, tmp_path):
        cv = load_cv(_cv_text(tmp_path, "See [[Some Note]].\n"))
        render_cv(cv)
        assert 'class="wikilink-dead">Some Note<' in cv.intro_html
        assert "href" not in cv.intro_html

    def test_wikilinks_resolve_with_a_path_map(self, tmp_path):
        cv = load_cv(_cv_text(tmp_path, "See [[post]].\n"))
        render_cv(cv, path_map={"post": "/post/"}, base_url="https://example.com")
        assert 'href="https://example.com/post/"' in cv.intro_html


class TestOutput:
    def test_phone_only_in_the_print_html(self):
        cv = _cv()
        render_cv(cv)
        page = render_cv_page(cv, SITE)
        assert PHONE not in page
        assert "Norwich, UK" in page and 'href="mailto:case@hey.com"' in page
        assert cv.phone == PHONE  # the CV itself is untouched
        printed = render_print_html(cv)
        assert PHONE in printed
        assert "@page" in printed  # cv.css is inlined

    def test_page_links_the_pdf_and_stylesheet(self):
        cv = _cv()
        render_cv(cv)
        page = render_cv_page(cv, SITE, static_files={"cv.css": "cv.abc123.css"})
        assert '<a href="https://example.com/cv/Paul-Hallett-CV.pdf">Download PDF</a>' in page
        assert 'href="https://example.com/static/cv.abc123.css"' in page
        assert '<article class="cv cv-sheet">' in page
        assert '<a href="https://github.com/phalt">github.com/phalt</a>' in page

    def test_pdf_is_one_a4_page(self, tmp_path):
        cv = _cv()
        render_cv(cv)
        path = write_pdf(cv, tmp_path / "out" / cv.pdf_name)
        assert path.read_bytes().startswith(b"%PDF")
        base_url = (DEFAULT_TEMPLATES / "static").as_uri() + "/"
        pages = _weasyprint_html()(string=render_print_html(cv), base_url=base_url).render().pages
        assert len(pages) == 1
        # A4 is 210 x 297 mm; WeasyPrint reports CSS pixels (96 per inch)
        assert (round(pages[0].width * 25.4 / 96), round(pages[0].height * 25.4 / 96)) == (210, 297)


class TestBuild:
    def test_writes_page_and_pdf(self, tmp_path):
        out = tmp_path / "_site"
        result = _build(_vault(tmp_path), out)
        assert "✓ cv.md → /cv/ (cv)" in result.output
        assert "→ _site/cv/index.html" in result.output
        assert "→ _site/cv/Paul-Hallett-CV.pdf" in result.output
        assert "Building 2 articles, 1 CV," in result.output
        assert "Built 2 articles, 1 CV," in result.output
        assert (out / "cv" / "Paul-Hallett-CV.pdf").read_bytes().startswith(b"%PDF")
        page = (out / "cv" / "index.html").read_text()
        assert PHONE not in page
        assert "Paul Hallett" in page and 'class="site-nav"' in page
        css = [p.name for p in (out / "static").glob("cv.*.css")]
        assert len(css) == 1 and f"/static/{css[0]}" in page
        assert (out / "static" / "fonts" / "inter-latin-ext-400-normal.woff2").is_file()

    def test_wikilink_to_the_cv_resolves(self, tmp_path):
        out = tmp_path / "_site"
        _build(_vault(tmp_path), out)
        assert 'href="https://example.com/cv/"' in (out / "index.html").read_text()

    def test_sitemap_but_not_feed_listings_tags_or_prev_next(self, tmp_path):
        out = tmp_path / "_site"
        _build(_vault(tmp_path), out)
        assert "<loc>https://example.com/cv/</loc>" in (out / "sitemap.xml").read_text()
        assert "/cv/" not in (out / "feed.xml").read_text()
        assert "/cv/" not in (out / "all" / "index.html").read_text()
        assert "/cv/" not in (out / "post" / "index.html").read_text()

    def test_sidebar_warning_is_printed(self, tmp_path):
        vault = _vault(tmp_path)
        text = (vault / "cv.md").read_text().replace("Hobbies]", "Hobbies, Hobbys]")
        (vault / "cv.md").write_text(text)
        result = _build(vault, tmp_path / "_site")
        assert "⚠ cv.md: sidebar section 'Hobbys' matches no section" in result.output
        assert "1 warning" in result.output

    def test_unpublished_cv_never_reaches_the_site(self, tmp_path):
        out = tmp_path / "_site"
        result = _build(_vault(tmp_path, cv_source=BESPOKE_MD), out)
        assert "✗ cv.md (publish is not true)" in result.output
        assert not (out / "cv").exists()
        assert not list(out.rglob("*.pdf"))
        assert not any(PHONE in p.read_text() for p in out.rglob("*.html"))

    def test_incremental_regenerates_the_pdf_only_when_the_cv_changes(self, tmp_path):
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        pdf = out / "cv" / "Paul-Hallett-CV.pdf"
        _build(vault, out)
        pdf.write_bytes(b"sentinel")

        result = _build(vault, out, "--incremental")
        assert "✓ cv.md (unchanged)" in result.output
        assert "Paul-Hallett-CV.pdf" not in result.output
        assert "Building 0 articles, 0 CVs," in result.output
        assert pdf.read_bytes() == b"sentinel"
        assert (out / "static" / "fonts").is_dir()  # static/ is recreated every build

        mtime = (vault / "cv.md").stat().st_mtime + 10
        os.utime(vault / "cv.md", (mtime, mtime))
        result = _build(vault, out, "--incremental")
        assert "✓ cv.md → rebuilt" in result.output
        assert "→ _site/cv/Paul-Hallett-CV.pdf" in result.output
        assert pdf.read_bytes().startswith(b"%PDF")

    def test_incremental_deletes_the_pdf_of_an_unpublished_cv(self, tmp_path):
        vault = _vault(tmp_path)
        out = tmp_path / "_site"
        _build(vault, out)
        assert (out / "cv" / "Paul-Hallett-CV.pdf").exists()
        shutil.copy(BESPOKE_MD, vault / "cv.md")
        result = _build(vault, out, "--incremental")
        assert "✗ cv.md (removed from output)" in result.output
        assert not (out / "cv").exists()

    def test_custom_templates_without_cv_files_fall_back_to_the_defaults(self, tmp_path):
        templates = tmp_path / "templates"
        shutil.copytree(DEFAULT_TEMPLATES, templates, ignore=shutil.ignore_patterns("reveal"))
        for name in ("cv.html", "cv_page.html", "_cv.html", "static/cv.css"):
            (templates / name).unlink()
        shutil.rmtree(templates / "static" / "fonts")
        out = tmp_path / "_site"
        _build(_vault(tmp_path), out, "--templates", str(templates))
        css = [p.name for p in (out / "static").glob("cv.*.css")]
        assert len(css) == 1 and f"/static/{css[0]}" in (out / "cv" / "index.html").read_text()
        assert (out / "static" / "fonts" / "inter-latin-400-normal.woff2").is_file()
        assert (out / "cv" / "Paul-Hallett-CV.pdf").read_bytes().startswith(b"%PDF")


class TestPdfCommand:
    def test_writes_only_the_pdf_and_ignores_publish(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
            result = runner.invoke(main, ["pdf", str(BESPOKE_MD)])
            assert result.exit_code == 0, result.output
            written = Path(cwd) / "Paul-Hallett-CV.pdf"
            assert f"→ {written}" in result.output
            assert written.read_bytes().startswith(b"%PDF")
            assert [p.name for p in Path(cwd).iterdir()] == ["Paul-Hallett-CV.pdf"]

    def test_output_option(self, tmp_path):
        result = _invoke("pdf", str(CV_MD), "-o", str(tmp_path / "out"))
        assert (tmp_path / "out" / "Paul-Hallett-CV.pdf").is_file()
        assert "Paul-Hallett-CV.pdf" in result.output

    def test_rejects_a_file_that_is_not_a_cv(self, tmp_path):
        result = _invoke("pdf", str(FIXTURES / "simple_article.md"), "-o", str(tmp_path), exit_code=1)
        assert "Error: Not a CV" in result.output
        assert "layout: cv" in result.output
        assert not list(tmp_path.iterdir())
