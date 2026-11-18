"""The Advanced Slides markdown pipeline: options, frontmatter and processor chain.

Port of ``src/obsidianMarkdownPreprocessor.ts``, ``src/yamlParser.ts`` and ``src/defaults.json``
from MSzturc/obsidian-advanced-slides (MIT). Processors run in exactly the upstream order.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import yaml

from paulblish.slides import processors as p
from paulblish.slides.jsre import compile_js

# src/defaults.json
DEFAULTS: dict = {
    "theme": "black",
    "highlightTheme": "zenburn",
    "template": "template/reveal.html",
    "separator": "\r?\n---\r?\n",
    "verticalSeparator": "\r?\n--\r?\n",
    "notesSeparator": "note:",
    "enableLinks": False,
    "title": "",
    "css": "",
    "width": 960,
    "height": 700,
    "margin": 0.04,
    "transition": "slide",
    "enableCustomControls": True,
    "timeForPresentation": 120,
    "log": False,
}

# The plugin's DEFAULT_SETTINGS (src/main.ts) — what Obsidian uses until settings are changed
GLOBAL_SETTINGS: dict = {
    "enableChalkboard": False,
    "enableOverview": False,
    "enableMenu": False,
    "enablePointer": False,
    "enableTimeBar": False,
    "theme": "black",
    "highlightTheme": "zenburn",
    "transition": "slide",
    "transitionSpeed": "default",
    "controls": True,
    "progress": True,
    "slideNumber": False,
    "showGrid": False,
}

# YamlParser.getRevealOptions — frontmatter keys forwarded to Reveal.initialize()
REVEAL_PROPS = [
    "width",
    "height",
    "margin",
    "minScale",
    "maxScale",
    "controls",
    "controlsTutorial",
    "controlsLayout",
    "controlsBackArrows",
    "progress",
    "slideNumber",
    "showSlideNumber",
    "hashOneBasedIndex",
    "hash",
    "respondToHashChanges",
    "history",
    "keyboard",
    "keyboardCondition",
    "disableLayout",
    "overview",
    "center",
    "touch",
    "loop",
    "rtl",
    "navigationMode",
    "shuffle",
    "fragments",
    "fragmentInURL",
    "embedded",
    "help",
    "pause",
    "showNotes",
    "autoPlayMedia",
    "preloadIframes",
    "autoAnimate",
    "autoAnimateMatcher",
    "autoAnimateEasing",
    "autoAnimateDuration",
    "autoAnimateUnmatched",
    "autoSlide",
    "autoSlideStoppable",
    "autoSlideMethod",
    "defaultTiming",
    "mouseWheel",
    "previewLinks",
    "postMessage",
    "postMessageEvents",
    "focusBodyOnPageVisibilityChange",
    "transition",
    "transitionSpeed",
    "backgroundTransition",
    "pdfMaxPagesPerSlide",
    "pdfSeparateFragments",
    "pdfPageHeightOffset",
    "viewDistance",
    "mobileViewDistance",
    "display",
    "hideInactiveCursor",
    "hideCursorTime",
    "markdown",
    "mermaid",
]

TEMPLATE_SETTINGS = (
    "enableOverview",
    "enableChalkboard",
    "enableMenu",
    "enableCustomControls",
    "enableTimeBar",
    "enablePointer",
)

_FRONT = re.compile(r"^(-{3}(?:\n|\r)([\w\W]+?)(?:\n|\r)-{3})?([\w\W]*)")


def load_front(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter the way ``yaml-front-matter``'s ``loadFront`` does.

    The returned markdown keeps everything after the closing ``---`` (including its newline).
    Invalid YAML yields no options and the whole input as markdown, as upstream.
    """
    text = text.removeprefix("﻿")
    match = _FRONT.match(text)
    options: dict = {}
    if match.group(2):
        try:
            loaded = yaml.safe_load(match.group(2))
        except yaml.YAMLError:
            return {}, text
        if isinstance(loaded, dict):
            options = {str(k): v for k, v in loaded.items()}
    content = match.group(3) or ""
    return options, content or text


def slide_options(frontmatter: dict) -> dict:
    """YamlParser.getSlideOptions: frontmatter, then plugin settings, then defaults."""
    return {**DEFAULTS, **GLOBAL_SETTINGS, **{k: v for k, v in frontmatter.items() if v is not None}}


def reveal_options(options: dict) -> dict:
    """YamlParser.getRevealOptions: the subset of options passed to ``Reveal.initialize``."""
    return {key: options[key] for key in REVEAL_PROPS if key in options}


def template_settings(options: dict) -> dict:
    return {key: options[key] for key in TEMPLATE_SETTINGS if key in options}


def _unresolved(_: str) -> None:
    return None


@dataclass
class Context:
    """Options plus the vault lookups the processors need (upstream: ``ObsidianUtils``)."""

    options: dict
    # Resolve a vault file referenced by name (![[img.png]], [[img.png]] in bg) to the URL to use
    find_file: Callable[[str], str | None] = _unresolved
    # Content of an embedded note / template, optionally just one heading or block (#^id)
    parse_file: Callable[[str, str | None], str | None] = lambda name, header: None
    # Rewrite a markdown image src or background image path to its published URL
    asset_url: Callable[[str], str | None] = _unresolved
    # Published URL of a wikilinked note, if it is on the site
    link_url: Callable[[str], str | None] = _unresolved
    vault_name: str = ""
    warnings: list[str] = field(default_factory=list)


def trim_ending(markdown: str, options: dict) -> str:
    text = markdown + "\n"
    for key in ("separator", "verticalSeparator"):
        found = compile_js(options[key], "gmi").search(text)
        if found and text.endswith(found.group(0)):
            return text[: text.rindex(found.group(0))]
    return markdown


def process(markdown: str, ctx: Context) -> str:
    """Run the full Advanced Slides processor chain over a deck's markdown body."""
    options = ctx.options
    multiple = p.MultipleFileProcessor(ctx)
    template = p.TemplateProcessor(ctx)

    before = trim_ending(markdown, options)
    after: str | None = None
    counter = 0
    while before != after:
        counter += 1
        if after:
            before = after
        after = template.process(multiple.process(before))
        # Default templates only apply on the first pass
        options["defaultTemplate"] = None
        if counter > 9:
            break

    text = after
    for processor in (
        p.SkipSlideProcessor(ctx),
        p.ReferenceProcessor(),
        p.DebugViewProcessor(ctx),
        p.AutoClosingProcessor(),
        p.DefaultBackgroundProcessor(ctx),
        p.CalloutProcessor(),
        p.EmojiProcessor(),
        p.IconsProcessor(),
        p.MermaidProcessor(),
        p.BlockProcessor(),
        p.FootnoteProcessor(ctx),
        p.ExcalidrawProcessor(ctx),
        p.ImageProcessor(ctx),
        p.InternalLinkProcessor(ctx),
        p.LatexProcessor(),
        p.FormatProcessor(),
        p.FragmentProcessor(ctx),
        p.DropProcessor(ctx),
        p.GridProcessor(ctx),
        p.CommentProcessor(ctx),
        p.ChartProcessor(ctx),
    ):
        text = processor.process(text)
    return text
