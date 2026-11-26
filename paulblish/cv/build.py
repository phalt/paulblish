"""Build CVs: parse a ``layout: cv`` file, split it into columns, render the web page and the PDF.

The text before the first ``##`` is the intro. Each ``##`` section goes to the right-hand column when
its name is listed in ``sidebar`` (case-insensitive), otherwise to the main column; both keep source
order. The web page (``cv_page.html``) never receives the phone number; the PDF (``cv.html``) does.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import replace
from pathlib import Path

import frontmatter

from paulblish.models import CV, Article, SiteConfig
from paulblish.renderer import _md
from paulblish.scanner import _resolve_date, _resolve_layout, _resolve_title
from paulblish.templating import _create_env, _og_context

DEFAULT_TEMPLATES = Path(__file__).parent.parent.parent / "templates"
CV_LAYOUT = "cv"


class NotACVError(ValueError):
    pass


def _str(value: object) -> str:
    return "" if value is None else str(value).strip()


def _sidebar(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()]
    return [_str(name) for name in value if _str(name)]


def load_cv(source_path: Path, relative_path: Path | None = None, url_path: str = "", slug: str = "") -> CV:
    """Parse a CV file. ``publish`` is ignored: ``pb pdf`` renders bespoke CVs that are never published."""
    post = frontmatter.load(source_path)
    meta = post.metadata
    if _resolve_layout(meta) != CV_LAYOUT:
        raise NotACVError(f"Not a CV: {source_path}\nAdd 'layout: cv' to its frontmatter.")
    title = _resolve_title(meta, source_path.name)
    # A bare filename, so a pdf_name can't write outside the CV's own directory
    pdf_name = Path(_str(meta.get("pdf_name"))).name or re.sub(r"\s+", "-", title.strip()) + "-CV.pdf"
    return CV(
        source_path=source_path,
        relative_path=relative_path or Path(source_path.name),
        title=title,
        slug=slug,
        url_path=url_path,
        date=_resolve_date(meta, source_path),
        body_markdown=post.content,
        tagline=_str(meta.get("tagline")),
        location=_str(meta.get("location")),
        email=_str(meta.get("email")),
        phone=_str(meta.get("phone")),
        github=_str(meta.get("github")),
        website=_str(meta.get("website")),
        pdf_name=pdf_name,
        sidebar=_sidebar(meta.get("sidebar")),
    )


def cv_from_article(article: Article) -> CV:
    """The CV for a scanned ``layout: cv`` article, keeping its place in the site."""
    cv = load_cv(article.source_path, article.relative_path, article.url_path, article.slug)
    cv.date = article.date
    return cv


def split_sections(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Split into the intro and ``(name, markdown)`` per top-level ``##`` section, in source order.

    Headings come from the parser, not a line regex, so a ``## `` inside a code fence doesn't split.
    """
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    tokens = _md.parse(text, {})
    starts = [
        (token.map[0], tokens[i + 1].content.strip())
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0 and token.map
    ]
    lines = text.split("\n")
    if not starts:
        return text, []
    intro = "\n".join(lines[: starts[0][0]])
    ends = [start for start, _ in starts[1:]] + [len(lines)]
    return intro, [(name, "\n".join(lines[start:end])) for (start, name), end in zip(starts, ends, strict=True)]


def render_cv(cv: CV, path_map: dict[str, str] | None = None, base_url: str = "") -> list[str]:
    """Render the intro and both columns into *cv*. Returns warnings for sidebar names with no section."""
    env: dict = {}
    if path_map:
        env["path_map"] = path_map
    if base_url:
        env["base_url"] = base_url

    intro, sections = split_sections(cv.body_markdown)
    wanted = {name.lower() for name in cv.sidebar}
    side = [md for name, md in sections if name.lower() in wanted]
    main = [md for name, md in sections if name.lower() not in wanted]
    # A blank line between sections, so a paragraph ending one can't run into the next one's heading
    cv.intro_html = _md.render(intro, dict(env))
    cv.main_html = _md.render("\n\n".join(main), dict(env))
    cv.side_html = _md.render("\n\n".join(side), dict(env))

    found = {name.lower() for name, _ in sections}
    return [
        f"{cv.relative_path}: sidebar section '{name}' matches no section"
        for name in cv.sidebar
        if name.lower() not in found
    ]


def _env(templates_dir: Path | None, static_files: dict[str, str] | None = None):
    # Custom template directories made before CV pages existed fall back to the default CV templates
    return _create_env([templates_dir, DEFAULT_TEMPLATES] if templates_dir else None, static_files=static_files)


def _static_file(templates_dir: Path | None, name: str) -> Path:
    if templates_dir and (custom := templates_dir / "static" / name).is_file():
        return custom
    return DEFAULT_TEMPLATES / "static" / name


def render_cv_page(
    cv: CV, site: SiteConfig, templates_dir: Path | None = None, static_files: dict[str, str] | None = None
) -> str:
    """The web page: the CV as a paper sheet inside the site chrome, without the phone number."""
    context = _og_context(site)
    context["page_title"] = f"{cv.title} — CV"
    context["page_url"] = site.base_url + cv.url_path
    if cv.tagline:
        context["page_description"] = cv.tagline
    template = _env(templates_dir, static_files).get_template("cv_page.html")
    # Blanked on the CV itself, so no template (custom ones included) can render it
    return template.render(cv=replace(cv, phone=""), site=site, **context)


def render_print_html(cv: CV, templates_dir: Path | None = None) -> str:
    """The standalone document WeasyPrint lays out: phone number included, cv.css inlined."""
    css = _static_file(templates_dir, "cv.css").read_text(encoding="utf-8")
    return _env(templates_dir).get_template("cv.html").render(cv=cv, css=css)


def _weasyprint_html():
    if sys.platform == "darwin":
        # Homebrew's pango is outside dyld's default search path, and SIP strips DYLD_* from processes
        # started through /usr/bin (make, env). cffi's find_library fallback reads this at load time.
        os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib:/usr/local/lib:/usr/lib")
    # Imported here so builds without CVs never need pango
    from weasyprint import HTML

    return HTML


def write_pdf(cv: CV, path: Path, templates_dir: Path | None = None) -> Path:
    """Write the one-page A4 PDF to *path*. Fonts resolve relative to the cv.css in use."""
    html = _weasyprint_html()
    base_url = _static_file(templates_dir, "cv.css").parent.as_uri() + "/"
    path.parent.mkdir(parents=True, exist_ok=True)
    html(string=render_print_html(cv, templates_dir), base_url=base_url).write_pdf(path)
    return path


def cv_output_path(cv: CV, output_dir: Path) -> Path:
    prefix = cv.url_path.strip("/")
    return (output_dir / prefix if prefix else output_dir) / "index.html"


def pdf_output_path(cv: CV, output_dir: Path) -> Path:
    return cv_output_path(cv, output_dir).parent / cv.pdf_name
