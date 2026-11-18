"""Port of reveal.js 4.3.1's markdown ``slidify`` (plugin/markdown/plugin.js, MIT).

Advanced Slides calls this server-side to split the processed markdown into
``<section data-markdown>`` elements; reveal.js's markdown plugin renders each one in the browser.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from paulblish.slides.jsre import compile_js

DEFAULT_SLIDE_SEPARATOR = "\r?\n---\r?\n"
DEFAULT_NOTES_SEPARATOR = "notes?:"
SCRIPT_END_PLACEHOLDER = "__SCRIPT_END__"

# Speaker notes are rendered at build time (upstream: marked with gfm)
_notes_md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def _markdown_slide(content: str, notes_separator: str) -> str:
    parts = compile_js(notes_separator, "mgi").split(content)
    if len(parts) == 2:
        content = parts[0] + '<aside class="notes">' + _notes_md.render(parts[1].strip()) + "</aside>"
    content = content.replace("</script>", SCRIPT_END_PLACEHOLDER)
    return '<script type="text/template">' + content + "</script>"


def slidify(
    markdown: str,
    separator: str | None = None,
    vertical_separator: str | None = None,
    notes_separator: str | None = None,
    attributes: str = "",
) -> str:
    separator = separator or DEFAULT_SLIDE_SEPARATOR
    notes_separator = notes_separator or DEFAULT_NOTES_SEPARATOR

    pattern = separator + ("|" + vertical_separator if vertical_separator else "")
    separator_regex = compile_js(pattern, "mg")
    horizontal = re.compile(separator)

    stack: list[str | list[str]] = []
    last = 0
    was_horizontal = True
    for match in separator_regex.finditer(markdown):
        is_horizontal = horizontal.search(match.group(0)) is not None
        if not is_horizontal and was_horizontal:
            stack.append([])
        content = markdown[last : match.start()]
        if is_horizontal and was_horizontal:
            stack.append(content)
        else:
            stack[-1].append(content)
        last = match.end()
        was_horizontal = is_horizontal

    remaining = markdown[last:]
    if was_horizontal:
        stack.append(remaining)
    else:
        stack[-1].append(remaining)

    sections = []
    for item in stack:
        if isinstance(item, list):
            inner = "".join(
                "<section data-markdown>" + _markdown_slide(child, notes_separator) + "</section>" for child in item
            )
            sections.append(f"<section {attributes}>{inner}</section>")
        else:
            sections.append(
                f"<section {attributes} data-markdown>" + _markdown_slide(item, notes_separator) + "</section>"
            )
    return "".join(sections)
