"""Build slide decks: scan the slides directory, resolve vault references, render reveal.js pages.

Every ``.md`` file in the slides directory with ``publish: true`` becomes ``/<slides>/<slug>/``,
rendered with the Advanced Slides pipeline (``preprocessor.py`` + ``slidify.py``) into
``templates/deck.html``. Images and stylesheets referenced by decks follow the article asset rule:
resolved anywhere in the vault and copied to ``/assets/``.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import frontmatter

from paulblish.assets import AssetRef
from paulblish.linker import _normalise
from paulblish.models import Deck, SiteConfig
from paulblish.scanner import SkippedFile, _resolve_date, _resolve_slug, _resolve_title
from paulblish.slides.preprocessor import (
    Context,
    load_front,
    process,
    reveal_options,
    slide_options,
    template_settings,
)
from paulblish.slides.runtime import CDN, HIGHLIGHT_THEMES, MATHJAX_URL
from paulblish.slides.slidify import slidify

DEFAULT_TEMPLATES = Path(__file__).parent.parent.parent / "templates"
RUNTIME_DIR = DEFAULT_TEMPLATES / "reveal"
RUNTIME_URL_PATH = "/static/reveal/"


# --- Scanning ------------------------------------------------------------------------------------


def find_slides_dir(source_dir: Path, name: str) -> Path | None:
    """Locate the slides directory under *source_dir*; a single-level name matches case-insensitively."""
    candidate = source_dir / name
    if candidate.is_dir():
        return candidate
    if "/" not in name:
        for child in sorted(source_dir.iterdir()):
            if child.is_dir() and child.name.lower() == name.lower():
                return child
    return None


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "deck"


def scan_decks(
    slides_dir: Path, source_dir: Path, include_drafts: bool = False
) -> tuple[list[Deck], list[SkippedFile]]:
    """Return publishable decks and the files that were skipped, with reasons."""
    prefix = slides_dir.relative_to(source_dir).as_posix().lower()
    decks: list[Deck] = []
    skipped: list[SkippedFile] = []
    seen_slugs: dict[str, Path] = {}

    for file_path in sorted(slides_dir.rglob("*.md")):
        relative_path = file_path.relative_to(source_dir)
        try:
            text = file_path.read_text(encoding="utf-8")
            metadata = frontmatter.loads(text).metadata
        except Exception as e:
            skipped.append(SkippedFile(path=relative_path, reason=f"failed to parse frontmatter: {e}"))
            continue

        if not include_drafts and str(metadata.get("publish", False)).lower() != "true":
            skipped.append(SkippedFile(path=relative_path, reason="publish is not true"))
            continue

        slug = _resolve_slug(metadata) or _slugify(file_path.stem)
        if slug in seen_slugs:
            skipped.append(
                SkippedFile(path=relative_path, reason=f"duplicate deck slug '{slug}' (also {seen_slugs[slug]})")
            )
            continue
        seen_slugs[slug] = relative_path

        decks.append(
            Deck(
                source_path=file_path,
                relative_path=relative_path,
                title=_resolve_title(metadata, file_path.name),
                slug=slug,
                url_path=f"/{prefix}/{slug}/",
                date=_resolve_date(metadata, file_path),
                text=text,
                description=str(metadata.get("description", "") or ""),
            )
        )
    return decks, skipped


def add_decks_to_path_map(path_map: dict[str, str], decks: list[Deck]) -> None:
    """Make decks wikilink targets (from articles and from other decks)."""
    for deck in decks:
        path_map.setdefault(_normalise(deck.source_path.stem), deck.url_path)
    for deck in decks:
        path_map.setdefault(_normalise(deck.title), deck.url_path)


# --- Vault lookups -------------------------------------------------------------------------------


class VaultIndex:
    """Every file in the vault by lowercase basename, for Obsidian-style name lookups."""

    def __init__(self, source_dir: Path, exclude: Path | None = None) -> None:
        self.source_dir = source_dir
        self.by_name: dict[str, list[Path]] = {}
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            if exclude is not None and path.is_relative_to(exclude):
                continue
            if any(part.startswith(".") for part in path.relative_to(source_dir).parts):
                continue
            self.by_name.setdefault(path.name.lower(), []).append(path)

    def find(self, ref: str, relative_to: Path | None = None) -> Path | None:
        """Exact path (vault root, then *relative_to*), then by basename anywhere in the vault."""
        ref = unquote(ref.strip()).lstrip("/")
        if not ref:
            return None
        for base in (self.source_dir, relative_to):
            if base is None:
                continue
            candidate = (base / ref).resolve()
            if candidate.is_file() and candidate.is_relative_to(self.source_dir.resolve()):
                return candidate
        matches = self.by_name.get(Path(ref).name.lower(), [])
        return matches[0] if matches else None


class AssetRegistry:
    """Hands out ``/assets/`` filenames for deck files, sharing names with article assets.

    A file that articles already publish keeps its name. A new file whose name is taken by a
    different file gets the content-hash prefix the article asset step uses for collisions.
    """

    def __init__(self, article_refs: list[AssetRef]) -> None:
        self.by_source: dict[Path, str] = {}
        self.taken: dict[str, Path] = {}
        for ref in article_refs:
            if ref.source_path is not None:
                source = ref.source_path.resolve()
                self.by_source.setdefault(source, ref.output_filename)
                self.taken.setdefault(ref.output_filename, source)
        self.new_refs: list[AssetRef] = []

    def add(self, source: Path) -> str:
        source = source.resolve()
        if source in self.by_source:
            return self.by_source[source]
        name = source.name
        if name in self.taken and self.taken[name] != source:
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:8]
            name = f"{digest}_{source.stem}{source.suffix}"
        self.by_source[source] = name
        self.taken[name] = source
        self.new_refs.append(AssetRef(original_ref=str(source), source_path=source, output_filename=name))
        return name


_URL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)
_YAML_BLOCK = re.compile(r"^---.*?---\n(.*?)($|---)", re.S)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def is_url(value: str) -> bool:
    return bool(_URL.match(value))


def _note_section(content: str, filename: str, header: str) -> str:
    """ObsidianUtils.parseFile with a subpath: one heading's section or one ``^block``."""
    lines = content.split("\n")
    start = end = None
    end_col = -1

    if header.startswith("^"):
        block = re.compile(rf"\s\^{re.escape(header[1:])}\s*$")
        for i, line in enumerate(lines):
            if block.search(line):
                end, end_col = i, len(line)
                start = i
                if not re.match(r"^\s*(?:[-*+]|\d+[.)])\s", line):
                    while start > 0 and lines[start - 1].strip():
                        start -= 1
                break
    else:
        wanted = " ".join(header.split()).lower()
        level = 0
        for i, line in enumerate(lines):
            m = _HEADING.match(line)
            if not m:
                continue
            if start is None and " ".join(m.group(2).split()).lower() == wanted:
                start, level = i, len(m.group(1))
            elif start is not None and len(m.group(1)) <= level:
                end, end_col = i, 0
                break

    if start is None:
        return "![[" + filename + "#" + header + "]]"
    return _substring(lines, start, 0, -1 if end is None else end, end_col)


def _substring(lines: list[str], start_line: int, start_col: int, end_line: int, end_col: int) -> str:
    """ObsidianUtils.substring."""
    result = ""
    last = len(lines) if end_line == -1 else end_line
    for index in range(start_line, last + 1):
        if index >= len(lines):
            continue
        line = lines[index]
        if index == start_line:
            result += line[start_col:] + "\n"
        elif index == last:
            piece = line[:end_col] if end_col > -1 else line
            if "^" in piece:
                piece = piece[: piece.rindex("^")]
            result += piece + "\n"
        else:
            result += line + "\n"
    return result


@dataclass
class DeckResolver:
    """The vault lookups for one deck (upstream: ObsidianUtils), producing published URLs."""

    deck: Deck
    index: VaultIndex
    registry: AssetRegistry
    site: SiteConfig
    path_map: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    @property
    def deck_dir(self) -> Path:
        return self.deck.source_path.parent

    def _asset(self, source: Path) -> str:
        return f"{self.site.base_url}/assets/{self.registry.add(source)}"

    def find_file(self, name: str) -> str | None:
        name = name.strip()
        if name.startswith("[[") and name.endswith("]]"):
            name = name[2:-2].strip()
        source = self.index.find(name, self.deck_dir)
        if source is None and name.lower().endswith(".excalidraw"):
            # Excalidraw drawings are published through their auto-exported SVG/PNG
            source = self.index.find(name + ".svg", self.deck_dir) or self.index.find(name + ".png", self.deck_dir)
        if source is None:
            if not is_url(name) and not name.startswith(self.site.base_url + "/assets/"):
                self.warnings.append(f"{self.deck.relative_path}: file not found: {name}")
            return None
        return self._asset(source)

    def asset_url(self, path: str) -> str | None:
        if not path or is_url(path) or path.startswith("#") or path.startswith(self.site.base_url + "/assets/"):
            return None
        source = self.index.find(path, self.deck_dir)
        return self._asset(source) if source is not None else None

    def parse_file(self, filename: str, header: str | None) -> str | None:
        name = filename.strip()
        if name.startswith("[[") and name.endswith("]]"):
            name = name[2:-2].strip()
        source = self.index.find(name, self.deck_dir)
        if source is None:
            self.warnings.append(f"{self.deck.relative_path}: embedded note not found: {filename}")
            return None
        content = source.read_text(encoding="utf-8")
        if header is None:
            m = _YAML_BLOCK.search(content)
            return m.group(1) if m else content
        return _note_section(content, filename, header)

    def link_url(self, target: str) -> str | None:
        name = target.split("#", 1)[0]
        url = self.path_map.get(_normalise(name)) if name.strip() else None
        return f"{self.site.base_url}{url}" if url else None

    def stylesheet(self, value: str, kind: str = "css") -> str:
        """URL for a theme / highlight theme / css entry (upstream resolves them against the plugin dir)."""
        value = str(value).strip()
        runtime = self.site.base_url + RUNTIME_URL_PATH
        if is_url(value):
            return value
        if kind == "theme" and (RUNTIME_DIR / "dist" / "theme" / f"{value}.css").is_file():
            return f"{runtime}dist/theme/{value}.css"
        if kind == "highlight" and value.lstrip("/") in HIGHLIGHT_THEMES:
            return HIGHLIGHT_THEMES[value.lstrip("/")].url
        bundled = value.lstrip("/")
        if bundled and (RUNTIME_DIR / bundled).is_file():
            return runtime + bundled
        source = self.index.find(value, self.deck_dir)
        if source is not None:
            return self._asset(source)
        self.warnings.append(f"{self.deck.relative_path}: stylesheet not found: {value}")
        return runtime + bundled


def _css_list(value) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


# --- Rendering -----------------------------------------------------------------------------------


def render_deck(
    deck: Deck,
    site: SiteConfig,
    index: VaultIndex,
    registry: AssetRegistry,
    path_map: dict[str, str],
    pele_url: str,
    templates_dir: Path | None = None,
) -> list[str]:
    """Render *deck* to ``deck.html``; returns warnings (missing files, stylesheets)."""
    from jinja2 import Environment, FileSystemLoader

    resolver = DeckResolver(deck=deck, index=index, registry=registry, site=site, path_map=path_map)
    yaml_options, markdown = load_front(deck.text)
    options = slide_options(yaml_options)
    # Reveal options are read before processing, as upstream (a chart's `height` doesn't leak)
    reveal = reveal_options(options)
    settings = template_settings(options)

    ctx = Context(
        options=dict(options),
        find_file=resolver.find_file,
        parse_file=resolver.parse_file,
        asset_url=resolver.asset_url,
        link_url=resolver.link_url,
        vault_name=index.source_dir.name,
    )
    processed = process(markdown, ctx)
    slides = slidify(
        processed,
        separator=options.get("separator"),
        vertical_separator=options.get("verticalSeparator"),
        notes_separator=options.get("notesSeparator"),
    )

    css_urls = [resolver.stylesheet(css) for css in _css_list(options.get("css"))]
    css_urls += _css_list(options.get("remoteCSS"))
    css_urls += [resolver.stylesheet(css) for css in site.slides_css]

    path = templates_dir if templates_dir and (templates_dir / "deck.html").is_file() else DEFAULT_TEMPLATES
    env = Environment(loader=FileSystemLoader(str(path)), autoescape=False)
    deck.html = env.get_template("deck.html").render(
        deck=deck,
        site=site,
        title=str(options.get("title") or deck.title),
        base=site.base_url + RUNTIME_URL_PATH,
        theme_url=resolver.stylesheet(options.get("theme", "black"), kind="theme"),
        highlight_theme_url=resolver.stylesheet(options.get("highlightTheme", "zenburn"), kind="highlight"),
        css_urls=css_urls,
        slides=slides,
        reveal_options_json=json.dumps(reveal, default=str),
        cdn=CDN,
        highlight_integrity=_highlight_integrity(options.get("highlightTheme", "zenburn")),
        mathjax_url=MATHJAX_URL,
        enable_custom_controls=bool(options.get("enableCustomControls")),
        enable_overview=bool(settings.get("enableOverview")),
        has_mermaid='class="mermaid"' in slides,
        pele_url=pele_url,
    )
    return resolver.warnings


def _highlight_integrity(value) -> str:
    theme = HIGHLIGHT_THEMES.get(str(value).strip().lstrip("/"))
    return theme.integrity if theme else ""


def deck_output_path(deck: Deck, output_dir: Path) -> Path:
    return output_dir / deck.url_path.strip("/") / "index.html"


def copy_runtime(output_dir: Path) -> Path:
    """Copy the vendored Advanced Slides themes and layout CSS to ``output/static/reveal/``."""
    target = output_dir / RUNTIME_URL_PATH.strip("/")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(RUNTIME_DIR, target)
    return target


def latest_date(decks: list[Deck]) -> datetime | None:
    return max((d.date for d in decks), default=None)
