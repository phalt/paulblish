"""Port of the Advanced Slides markdown processors (``src/processors/*.ts``, MIT).

Each processor rewrites the deck's markdown before reveal.js's markdown plugin sees it. They are
ported line for line, keeping JavaScript's string/RegExp semantics (see ``jsre.py``), because
several of them depend on those semantics for their output.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING

from paulblish.slides.jsre import (
    JSRegExp,
    compile_js,
    replace_all_str,
    replace_re,
    replace_str,
    split_join,
)
from paulblish.slides.properties import CommentParser, Properties

if TYPE_CHECKING:
    from paulblish.slides.preprocessor import Context

_EMOJI: dict[str, str] = json.loads((Path(__file__).parent / "data" / "emoji.json").read_text())


def _separators(ctx: Context) -> tuple[re.Pattern[str], re.Pattern[str]]:
    return compile_js(ctx.options["separator"], "gmi"), compile_js(ctx.options["verticalSeparator"], "gmi")


def _slides(markdown: str, ctx: Context):
    """Yield every slide of *markdown*, split the way the processors split it."""
    horizontal, vertical = _separators(ctx)
    for group in horizontal.split(markdown):
        yield from vertical.split(group)


def _extract_notes(slide: str, ctx: Context) -> tuple[str, str]:
    separator = ctx.options.get("notesSeparator") or "note:"
    index = slide.find(separator)
    if index > 0:
        return slide[:index], slide[index:]
    return slide, ""


_SLIDE_COMMENT = re.compile(r"<!--\s*(?:\.)?slide.*-->")


# --- Multiple files (![[Note]] / ![[Note#Heading]]) ---------------------------------------------


class MultipleFileProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.regex = JSRegExp(r"!\[\[(.*)\]\]", "gm")
        self.image_regex = re.compile(
            r"!\[\[(.*(?:jpg|png|jpeg|gif|bmp|webp|svg))\s*\|?\s*([^\]]*)??\]\]\s?(<!--.*-->)?", re.I
        )

    def process(self, markdown: str) -> str:
        lines = markdown.split("\n")
        out = []
        for line in lines:
            if self.regex.test(line) and not self.image_regex.search(line):
                out.append(self._transform_line(line))
            else:
                out.append(line)
        return "\n".join(out)

    def _transform_line(self, line: str) -> str:
        comment = line[line.index("<!--") :] if "<!--" in line else ""
        link = replace_str(replace_str(line, "![[", ""), "]]", "")
        link = replace_str(link, comment, "").strip()
        header = None
        if "#" in link:
            parts = link.split("#")
            link, header = parts[0], parts[1]

        if re.search(r"(.*\.excalidraw)", link, re.I):
            return line  # Excalidraw drawings are images, not notes
        filename = link if link.lower().endswith(".md") else link + ".md"

        content = self.ctx.parse_file(filename, header)
        if content:
            return self.process(content + comment if comment else content)
        return line


# --- Templates (<!-- slide template="[[tpl]]" -->) -----------------------------------------------


class TemplateProcessor:
    _empty_slide_comment = re.compile(r"<!--\s*(?:\.)?slide(?::)?\s*-->")
    _template_comment = re.compile(r"<!--\s*(?:\.)?slide.*(template=\"\[\[([^\]]+)\]\]\"\s*).*-->")
    _property = re.compile(r":::\s([^\n]+)\s*(.*?:::[^\n]*)", re.S)

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self._optional = JSRegExp(r"<%\?.*%>", "g")
        self.parser = CommentParser(ctx)
        self.multiple_file = MultipleFileProcessor(ctx)
        self.footnotes = FootnoteProcessor(ctx)

    def process(self, markdown: str) -> str:
        ctx = self.ctx
        text = markdown
        default_template = ctx.options.get("defaultTemplate")
        if default_template is not None:
            for slide in _slides(markdown, ctx):
                found = _SLIDE_COMMENT.search(slide)
                if found:
                    annotation = found.group(0)
                    comment = self.parser.parse_line(annotation)
                    if not comment.has_attribute("template"):
                        comment.add_attribute("template", default_template, False)
                    replaced = split_join(slide, annotation, self.parser.comment_to_string(comment))
                    text = split_join(text, slide, replaced)
                else:
                    text = split_join(text, slide, f'<!-- slide template="{default_template}" -->\n' + slide)

        output = text
        for slide in _slides(text, ctx):
            if not self._template_comment.search(slide):
                continue
            md, notes = _extract_notes(slide, ctx)
            counter = 0
            try:
                while self._template_comment.search(md):
                    counter += 1
                    md = self._transform_slide(md)
                    if counter > 9:
                        break
            except _TemplateError:
                continue  # upstream logs "Cannot process template" and keeps the slide as is
            md = self._empty_slide_comment.sub("", md)
            md = md.strip()
            md = self._compute_variables(md)
            if notes:
                md += "\n\n" + notes
            output = split_join(output, slide, md)
        return output

    def _transform_slide(self, slide: str) -> str:
        found = self._template_comment.search(slide)
        if not found:
            return slide
        template_property, file = found.group(1), found.group(2)
        filename = file if file.endswith(".md") else file + ".md"
        content = self.ctx.parse_file(filename, None)
        if content is None:
            # Upstream throws here; the caller logs it and leaves the slide unchanged
            raise _TemplateError(filename)
        content = self.multiple_file.process(content)
        return split_join(content, "<% content %>", split_join(slide, template_property, ""))

    def _compute_variables(self, slide: str) -> str:
        result = slide
        for m in self._property.finditer(slide):
            match, name, content = m.group(0), m.group(1), m.group(2)
            if "<!--" in name:
                name = name[: name.index("<!--")]
            if name.strip() == "block":
                continue
            content = "::: block\n" + content
            optional_name = "<%? " + name.strip() + " %>"
            name = "<% " + name.strip() + " %>"
            result = replace_all_str(result, optional_name, content + "\n" + optional_name)
            result = replace_all_str(result, name, content)
            result = replace_all_str(result, match, "")
        result = self.footnotes.transform_footnotes(result)
        # Remove optional template variables. The regex is global and shared, so (as upstream)
        # `lastIndex` carries over between removals and between slides.
        regex = self._optional
        while (m := regex.exec(result)) is not None:
            if m.start() == regex.last_index:
                regex.last_index += 1
            result = replace_all_str(result, m.group(0), "")
        return result


class _TemplateError(Exception):
    pass


# --- Skip slides, block references, debug grid, self-closing tags --------------------------------


class SkipSlideProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.parser = CommentParser(ctx)

    def process(self, markdown: str) -> str:
        output = markdown
        for slide in _slides(markdown, self.ctx):
            new_slide = slide
            found = _SLIDE_COMMENT.search(slide)
            if found:
                comment = self.parser.parse_line(found.group(0))
                if comment.has_attribute("skip") and comment.get_attribute("skip") == "true":
                    new_slide = '<!-- slide data-visibility="hidden" -->'
            # JS replace(): first occurrence, `$` patterns in the replacement are expanded
            output = replace_str(output, slide, new_slide)
        return output


class ReferenceProcessor:
    _ref = re.compile(r"\^[\w-]+\s", re.A)

    def process(self, markdown: str) -> str:
        return self._ref.sub("", markdown)


class DebugViewProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        output = markdown
        if self.ctx.options.get("showGrid"):
            for slide in _slides(markdown, self.ctx):
                md, notes = _extract_notes(slide, self.ctx)
                new_slide = self._add_debug_code(md)
                if notes:
                    new_slide += "\n\n" + notes
                output = replace_str(output, slide, new_slide)
        return output

    @staticmethod
    def _add_debug_code(markdown: str) -> str:
        rows = "".join(f'<grid drag="100 10" drop="0 {i * 10}" border="thin dotted blue"/>\n' for i in range(10))
        cols = "".join(f'<grid drag="10 100" drop="{i * 10} 0" border="thin dotted blue"/>\n' for i in range(10))
        return markdown + "\n" + rows + cols


class AutoClosingProcessor:
    _regex = re.compile(r"<(\s*?([\w]*)[^>]*?)/(?<=/)>", re.M | re.A)

    def process(self, markdown: str) -> str:
        return self._regex.sub(lambda m: f"<{m.group(1)}></{m.group(2) or ''}>", markdown)


# --- Default background (frontmatter `bg`) -------------------------------------------------------


class DefaultBackgroundProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.parser = CommentParser(ctx)

    def process(self, markdown: str) -> str:
        output = markdown
        bg = self.ctx.options.get("bg")
        if bg:
            bg = str(bg)
            if bg in ("transparent", "rgba(0,0,0,0)"):
                output = "<style>\nbody {\n\tbackground-color: rgba(0,0,0,0) !important;\n}\n</style>\n" + output
            for slide in _slides(markdown, self.ctx):
                if slide:
                    output = split_join(output, slide, self._transform_slide(slide, bg))
        return output

    def _transform_slide(self, slide: str, bg: str) -> str:
        found = _SLIDE_COMMENT.search(slide)
        if found:
            comment = self.parser.parse_line(found.group(0))
            if not comment.has_attribute("data-background-image") and not comment.has_attribute(
                "data-background-color"
            ):
                comment.add_attribute("bg", bg)
            return replace_re(slide, _SLIDE_COMMENT, self.parser.comment_to_string(comment), count_all=False)
        return slide + f'\n<!-- slide bg="{bg}" -->\n'


# --- Callouts ------------------------------------------------------------------------------------

_CALLOUT_COLORS = {
    **dict.fromkeys(("abstract", "summary", "tldr", "info"), "callout-color1"),
    **dict.fromkeys(("todo", "tip", "hint", "important"), "callout-color2"),
    **dict.fromkeys(("success", "check", "done"), "callout-color3"),
    **dict.fromkeys(("question", "help", "faq"), "callout-color4"),
    **dict.fromkeys(("warning", "caution", "attention"), "callout-color5"),
    **dict.fromkeys(("failure", "fail", "missing"), "callout-color6"),
    **dict.fromkeys(("danger", "error", "bug"), "callout-color7"),
    "example": "callout-color8",
    **dict.fromkeys(("quote", "cite"), "callout-color9"),
}

_CALLOUT_ICONS = {
    **dict.fromkeys(("abstract", "summary", "tldr"), ":fas_clipboard-list:"),
    "info": ":fas_info-circle:",
    "todo": ":fas_check-circle:",
    **dict.fromkeys(("tip", "hint", "important"), ":fas_fire-alt:"),
    **dict.fromkeys(("success", "check", "done"), ":fas_check:"),
    **dict.fromkeys(("question", "help", "faq"), ":fas_question-circle:"),
    **dict.fromkeys(("warning", "caution", "attention"), ":fas_exclamation-triangle:"),
    **dict.fromkeys(("failure", "fail", "missing"), ":fas_times:"),
    **dict.fromkeys(("danger", "error"), ":fas_bolt:"),
    "bug": ":fas_bug:",
    "example": ":fas_list:",
    **dict.fromkeys(("quote", "cite"), ":fas_quote-left:"),
}


class CalloutProcessor:
    _regex = re.compile(r">\s\[!([^\]]+)\]-* *(.*)")

    def process(self, markdown: str) -> str:
        lines = markdown.split("\n")
        out: list[str] = []
        start = -1
        add = True
        for i, line in enumerate(lines):
            if line.strip().startswith(">") and start == -1:
                start = i
                add = False
            elif not line.strip().startswith(">") and start > -1:
                out.extend(self._transform_block(lines, start, i - 1))
                start = -1
                add = True
            if add:
                out.append(line)
        return "\n".join(out)

    def _transform_block(self, lines: list[str], start: int, end: int) -> list[str]:
        found = self._regex.search(lines[start])
        if not found:
            return lines[start : end + 1]
        kind, title_line = found.group(1), found.group(2)
        key = kind.lower()
        title = title_line if title_line else kind[0].upper() + kind[1:].lower()
        result = [
            f'<div class="callout {_CALLOUT_COLORS.get(key, "callout-color-default")}">',
            '<div class="callout-title">',
            '<div class="callout-icon">',
            "",
            _CALLOUT_ICONS.get(key, ":fas_pencil-alt:"),
            "",
            "</div>",
            '<div class="callout-title-inner">',
            "",
            title,
            "",
            "</div>",
            "</div>",
            '<div class="callout-content">',
        ]
        for i in range(start + 1, end + 1):
            result.append("")
            result.append(lines[i].strip()[1:].strip())
        result += ["", "</div>", "</div>"]
        return result


# --- Emoji, icons, mermaid, blocks ---------------------------------------------------------------


class EmojiProcessor:
    _regex = re.compile(r"(:(\w|\+|-)+:)(?=|[!.?]|$)", re.I | re.M | re.A)

    def process(self, markdown: str) -> str:
        return self._regex.sub(lambda m: _EMOJI.get(m.group(0), m.group(0)), markdown)


class IconsProcessor:
    _regex = re.compile(r":(fas|far|fal|fad|fab)_([\w-]+):", re.A)

    def process(self, markdown: str) -> str:
        return self._regex.sub(lambda m: f"![]({m.group(1)} fa-{m.group(2)})", markdown)


class MermaidProcessor:
    def process(self, markdown: str) -> str:
        while True:
            start = markdown.find("```mermaid")
            if start < 0:
                return markdown
            end = markdown.find("```", start + 11)
            if end < 0:
                return markdown
            before, after = markdown[:start], markdown[end + 3 :]
            content = markdown[start + 11 : end]
            markdown = before + "\n" + '<div class="mermaid">' + "\n" + content + "\n" + "</div>" + "\n" + after


class BlockProcessor:
    _open = re.compile(r":::\sblock\s*")

    def process(self, markdown: str) -> str:
        markdown = self._open.sub('<div class="block">\n\n', markdown)
        return replace_all_str(markdown, ":::", "</div>\n\n")


# --- Footnotes -----------------------------------------------------------------------------------


class FootnoteProcessor:
    _regex = re.compile(r"\[\^([^\]]*)]", re.I | re.M)

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        output = markdown
        for slide in _slides(markdown, self.ctx):
            if self._regex.search(slide):
                output = replace_str(output, slide, self.transform_footnotes(slide))
        return output

    def transform_footnotes(self, markdown: str) -> str:
        if not self._regex.search(markdown):
            return markdown
        text = markdown
        note_index = 1
        notes: dict[str, str] = {}
        while found := self._regex.search(text):
            token, key = found.group(0), found.group(1)
            lines = []
            for line in text.split("\n"):
                if token in line:
                    if token + ": " in line:
                        if key not in notes:
                            notes[key] = line.split(token + ": ")[1]
                        lines.append("")
                    else:
                        parts = line.split(token)
                        result = parts[0].strip()
                        result += f'<sup id="fnref:{key}" role="doc-noteref">{note_index}</sup>'
                        result += parts[1].strip()
                        note_index += 1
                        lines.append(result)
                else:
                    lines.append(line)
            text = "\n".join(lines)

        block = '<div class="footnotes" role="doc-endnotes">\n<ol>\n'
        for key, value in notes.items():
            block += f'<li id="fn:{key}" role="doc-endnote" class="footnote"><p>\n\n{value}\n\n</p></li>'
        block += "</ol>\n</div>\n"

        placeholder = "<%? footnotes %>"
        if placeholder in text:
            return replace_all_str(text, placeholder, block)
        return text + "\n" + block


# --- Excalidraw and images -----------------------------------------------------------------------


class ExcalidrawProcessor:
    _regex = re.compile(r"!\[\[(.*\.excalidraw)\|?([^\]]*)??\]\]\s?(<!--.*-->)?", re.I)

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        return "\n".join(
            self._transform_line(line) if self._regex.search(line) else line for line in markdown.split("\n")
        )

    def _transform_line(self, line: str) -> str:
        found = self._regex.search(line)
        image, ext, comment = found.group(1), found.group(2), found.group(3)
        found_file = self.ctx.find_file(image)
        image_file = image if found_file is None else found_file
        suffix = "" if ext is None else "|" + ext
        return f"![[{image_file}{suffix}]] {comment or ''}"


class ImageProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.parser = CommentParser(ctx)
        self.markdown_image = JSRegExp(
            r"^[ ]{0,3}!\[([^\]]*)\]\((.*(?:jpg|png|jpeg|gif|bmp|webp|svg)?)\)\s?(<!--.*-->)?", "gim"
        )
        self.obsidian_image = JSRegExp(
            r"!\[\[(.*?(?:jpg|png|jpeg|gif|bmp|webp|svg))\s*\|?\s*([^\]]*)??\]\]\s?(<!--.*-->)?", "ig"
        )
        self.obsidian_reference = JSRegExp(r"\[\[(.*?(?:jpg|png|jpeg|webp|gif|bmp|svg))\|?([^\]]*)??\]\]", "gi")

    def process(self, markdown: str) -> str:
        first = []
        for line in markdown.split("\n"):
            if self.obsidian_image.test(line):
                first.append(self._transform_image_string(line))
            elif self.obsidian_reference.test(line):
                first.append(self._transform_reference_string(line))
            else:
                first.append(line)
        second = [self._htmlify(line) if self.markdown_image.test(line) else line for line in first]
        return "\n".join(second)

    def _find(self, image: str) -> str:
        found = self.ctx.find_file(image)
        return image if found is None else found

    def _transform_reference_string(self, line: str) -> str:
        result = line
        regex = self.obsidian_reference
        regex.last_index = 0
        while (m := regex.exec(result)) is not None:
            if m.start() == regex.last_index:
                regex.last_index += 1
            result = replace_all_str(result, m.group(0), self._find(m.group(1)))
        return result

    def _transform_image_string(self, line: str) -> str:
        result = ""
        regex = self.obsidian_image
        regex.last_index = 0
        while (m := regex.exec(line)) is not None:
            if m.start() == regex.last_index:
                regex.last_index += 1
            image, ext, comment = m.group(1), m.group(2), m.group(3)
            file_path = self._find(image)
            comment_string = self._build_comment(ext, comment) or ""
            result = result + f"\n![]({file_path}) {comment_string}"
        return result

    def _build_comment(self, ext: str | None, comment_string: str | None) -> str:
        comment = self.parser.parse_comment(comment_string) if comment_string else self.parser.build_comment("element")
        if ext:
            if "x" in ext:
                parts = ext.split("x")
                width, height = parts[0], parts[1]
            else:
                width, height = ext, None
            comment.add_style("width", f"{width}px")
            if height:
                comment.add_style("height", f"{height}px")
        return self.parser.comment_to_string(comment)

    def _htmlify(self, line: str) -> str:
        result = ""
        regex = self.markdown_image
        regex.last_index = 0
        while (m := regex.exec(line)) is not None:
            if m.start() == regex.last_index:
                regex.last_index += 1
            alt, file_path, comment_string = m.group(1), m.group(2), m.group(3)
            if alt and "|" in alt:
                comment_string = self._build_comment(alt.split("|")[1], comment_string) or ""

            comment = self.parser.parse_line(comment_string) or self.parser.build_comment("element")
            if result:
                result += "\n"

            if file_path.startswith(("fas", "far", "fal", "fad", "fab")):
                result += f'<i class="{file_path}" {self.parser.build_attributes(comment)}></i>'
                continue

            resolved = self.ctx.asset_url(file_path)
            if resolved is not None:
                file_path = resolved
            elif file_path.startswith("file:/"):
                # Upstream serves files outside the vault through its local server
                from urllib.parse import urlparse

                file_path = "/localFileSlash" + urlparse(file_path).path

            if comment.has_style("width"):
                comment.add_style("object-fit", "fill")
            if not comment.has_style("align-self") and comment.has_attribute("align"):
                align = comment.get_attribute("align")
                if align == "left":
                    comment.add_style("align-self", "start")
                elif align == "right":
                    comment.add_style("align-self", "end")
                elif align == "center":
                    comment.add_style("align-self", "center")
                elif align == "stretch":
                    comment.add_style("align-self", "stretch")
                    comment.add_style("object-fit", "cover")
                    comment.add_style("height", "100%")
                    comment.add_style("width", "100%")
                comment.delete_attribute("align")
            if not comment.has_style("object-fit"):
                comment.add_style("object-fit", "scale-down")
            result += f'<img src="{file_path}" alt="{alt}" {self.parser.build_attributes(comment)}>'
        return result + "\n"


# --- Internal links ([[Note]] / [[Note|Alias]]) --------------------------------------------------


class InternalLinkProcessor:
    _regex = re.compile(r"(?:(?<=[^!])|^)\[\[(?:(.*?)\|)?([^\]]*)\]\]", re.M)

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        return self._regex.sub(self._link, markdown)

    def _link(self, m: re.Match[str]) -> str:
        target, text = m.group(1), m.group(2)
        # Paulblish addition: link to the published page when the note is on the site.
        # Otherwise fall back to upstream behaviour (plain text unless `enableLinks` is set).
        url = self.ctx.link_url(target if target is not None else text)
        if url is not None:
            return f"[{text}]({url})"
        if self.ctx.options.get("enableLinks"):
            from urllib.parse import quote

            vault = quote(self.ctx.vault_name, safe="~@#$&()*!+=:;,?/'")
            file = quote(target if target is not None else text, safe="~@#$&()*!+=:;,?/'")
            return f"[{text}](obsidian://open?vault={vault}&file={file})"
        return text


# --- Maths ---------------------------------------------------------------------------------------


class LatexProcessor:
    _single = re.compile(r"\$(.*?)\$")

    def process(self, markdown: str) -> str:
        text = self._mark(markdown)
        text = self._multi_line(text)
        text = self._mark(text)
        text = self._single_line(text)
        return self._unmark(text)

    @staticmethod
    def _mark(markdown: str) -> str:
        markdown = markdown.replace("\\$", "~~d~~")
        markdown = markdown.replace("`$$", "~~s~~").replace("$$`", "~~e~~")
        return markdown.replace("`$", "~~ss~~").replace("$`", "~~se~~")

    @staticmethod
    def _unmark(markdown: str) -> str:
        # JS replaceAll expands `$$` in the replacement, so '$$$$`' inserts '$$`'
        return (
            markdown.replace("~~d~~", "\\$")
            .replace("~~e~~", "$$`")
            .replace("~~s~~", "`$$")
            .replace("~~ss~~", "`$")
            .replace("~~se~~", "$`")
        )

    def _single_line(self, markdown: str) -> str:
        lines = []
        for line in markdown.split("\n"):
            if "$" in line:
                line = self._single.sub(lambda m: f"`${m.group(1)}$`", line)
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _multi_line(markdown: str) -> str:
        if "$$" not in markdown:
            return markdown
        parts = markdown.split("$$")
        wrapped = [part if i & 1 else "`" + part + "`" for i, part in enumerate(parts)]
        return "$$".join(wrapped)[1:-1]


# --- Formatting (__bold__, ==mark==, %%comments%%) -----------------------------------------------


class FormatProcessor:
    _bold = re.compile(r"(?:(?<=[^_])|^)__([^_]+)__(?!_)", re.M)
    _mark = re.compile(r"==([^=]*)==", re.M)
    _comment = re.compile(r"%%([^%]*)%%", re.M)

    def _apply(self, text: str) -> str:
        text = self._bold.sub(lambda m: f"**{m.group(1).strip()}**", text)
        text = self._mark.sub(lambda m: f"<mark>{m.group(1)}</mark>", text)
        return self._comment.sub("", text)

    def process(self, markdown: str) -> str:
        inside_code = False
        lines = []
        for line in markdown.split("\n"):
            if "```" in line:
                inside_code = not inside_code
            if inside_code:
                lines.append(line)
                continue
            parts = line.split("`")
            if len(parts) > 1:
                for i in range(0, len(parts), 2):
                    parts[i] = self._apply(parts[i])
                lines.append("`".join(parts))
            else:
                lines.append(self._apply(line))
        return self._comment.sub("", "\n".join(lines))


# --- Fragments (+ lists, 1) lists) ---------------------------------------------------------------


class FragmentProcessor:
    _code_block = re.compile(r"```[^\n]*(?:\n[^`]*\n)```")

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.parser = CommentParser(ctx)
        self.counter = 1
        self.ordered_list = JSRegExp(r"^\d\) ", "g")

    def process(self, markdown: str) -> str:
        separator = compile_js(f"{self.ctx.options['separator']}|{self.ctx.options['verticalSeparator']}", "gmi")
        code_lines = [
            (markdown[: m.start()].count("\n"), markdown[: m.end()].count("\n"))
            for m in self._code_block.finditer(markdown)
        ]
        out = []
        for number, line in enumerate(markdown.split("\n")):
            if separator.search(f"\n{line}\n"):
                self.counter = 1
                out.append(line)
                continue
            if any(start <= number <= end for start, end in code_lines):
                out.append(line)
                continue
            if line.strip().startswith("+ ") or self.ordered_list.test(line.strip()):
                out.append(self._transform_line(line))
            else:
                out.append(line)
        return "\n".join(out)

    def _transform_line(self, line: str) -> str:
        comment = self.parser.parse_line(line) or self.parser.build_comment("element")
        if "<!--" in line:
            line = line[: line.index("<!--")]
        if not comment.has_attribute("data-fragment-index"):
            comment.add_attribute("data-fragment-index", str(self.counter))
            if not comment.has_class("fragment"):
                comment.add_class("fragment")
            self.counter += 1
        extra = "&shy;" + self.parser.comment_to_string(comment)
        line = replace_str(line, "+ ", "- " + extra)
        return replace_re(line, self.ordered_list, "1. " + extra, count_all=True)


# --- Drop (wrap every slide in an absolute grid) -------------------------------------------------


class DropProcessor:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.parser = CommentParser(ctx)

    def process(self, markdown: str) -> str:
        output = markdown
        for slide in _slides(markdown, self.ctx):
            if not slide.strip():
                continue
            new_slide = self._transform_slide(slide)
            # Upstream: replace the first occurrence and keep any later ones as they are
            parts = output.split(slide)
            output = new_slide.join([parts[0], slide.join(parts[1:])])
        return output

    def _transform_slide(self, slide: str) -> str:
        md, notes = _extract_notes(slide, self.ctx)
        found = _SLIDE_COMMENT.search(md)
        if found:
            comment = self.parser.parse_line(found.group(0))
            comment.add_class("drop")
            out_md = _SLIDE_COMMENT.sub("", md, count=1).strip()
            out_comment = self.parser.comment_to_string(comment)
        else:
            out_md = md.strip()
            out_comment = '<!-- .slide: class="drop" -->'
        out = f'{out_comment}\n<grid absolute="true" drag="100 100" drop="0 0">\n{out_md}\n</grid>'
        if notes:
            out += "\n\n" + notes
        return out


# --- Grid (<grid drag="" drop="">) ---------------------------------------------------------------


class GridProcessor:
    _block = re.compile(r"<\s*grid(?:(?!(<grid|</grid>)).)*</grid>", re.S)
    _grid = re.compile(r"<\s*grid([^>]+)>(.*?)</grid>", re.S)
    _properties = re.compile(r"([^=]*)\s*=\s*\"([^\"]*)\"\s*|([^=]*)\s*=\s*'([^']*)'\s*")

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        output = markdown
        for slide in _slides(markdown, self.ctx):
            if self._block.search(slide):
                before = self._transform_slide(slide)
                after = None
                while after != before:
                    if after is not None:
                        before = after
                    after = self._transform_slide(before)
                output = split_join(output, slide, after)
        return output

    def _transform_slide(self, slide: str) -> str:
        result: dict[str, str] = {}
        for m in self._block.finditer(slide):
            grid = self._grid.search(m.group(0))
            result[grid.group(0)] = self._transform_grid(grid.group(1), grid.group(2))
        for key, value in result.items():
            if value:
                slide = split_join(slide, key, value)
        return slide

    def _transform_grid(self, attr: str, inner: str) -> str:
        properties = Properties(self._parse_attributes(attr.strip()), self.ctx)
        return (
            f'<div class="{properties.get_classes()}" style="{properties.get_styles()}" '
            f"{properties.get_attributes()}>\n{inner}</div>"
        )

    def _parse_attributes(self, attributes: str) -> dict[str, str]:
        # Upstream destructures `[, key, value]`, so single-quoted values set key `undefined`
        result: dict[str, str] = {}
        for m in self._properties.finditer(attributes):
            if m.group(1) is not None:
                result[m.group(1)] = m.group(2)
            else:
                result["undefined"] = "undefined"
        return result


# --- Comments (normalise every <!-- element/slide --> annotation) --------------------------------


class CommentProcessor:
    _read = re.compile(r"<!--.*-->")

    def __init__(self, ctx: Context) -> None:
        self.parser = CommentParser(ctx)

    def process(self, markdown: str) -> str:
        lines = []
        for line in markdown.split("\n"):
            if self.parser.line_has_comment(line):
                replacement = self.parser.comment_to_string(self.parser.parse_line(line))
                line = replace_re(line, self._read, replacement, count_all=False)
            lines.append(line)
        return "\n".join(lines)


# --- Charts (```chart blocks) --------------------------------------------------------------------

_CHART_COLORS = ["#4285f4", "#ea4335", "#fbbc05", "#34a853", "#673ab7", "#cccccc", "#777777"]


def _js_json(value: str):
    """``JSON.parse`` the way chart settings use it; raises ValueError on bad input like JS."""
    return json.loads(value)


def _json_stringify(value) -> str:
    def _default(o):
        raise TypeError(o)

    def _fix(o):
        if isinstance(o, float) and o.is_integer() and math.isfinite(o):
            return int(o)
        if isinstance(o, dict):
            return {k: _fix(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_fix(v) for v in o]
        return o

    return json.dumps(_fix(value), separators=(",", ":"), ensure_ascii=False, default=_default)


class ChartProcessor:
    _type = re.compile(r"type:\s(\w*)", re.A)
    _labels = re.compile(r"labels:\s(.*)")
    _dataset = re.compile(r"title:\s(.*)\s*data:\s(.*)")
    _settings = {
        name: re.compile(rf"({name}):\s(.*)")
        for name in (
            "spanGaps",
            "tension",
            "beginAtZero",
            "legend",
            "legendPosition",
            "stacked",
            "height",
            "useThemeColors",
        )
    }

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def process(self, markdown: str) -> str:
        while True:
            start = markdown.find("```chart")
            if start < 0:
                return markdown
            end = markdown.find("```", start + 11)
            if end < 0:
                return markdown
            before, after = markdown[:start], markdown[end + 3 :]
            markup = markdown[start + 8 : end]
            type_match = self._type.search(markup)
            label_match = self._labels.search(markup)
            if not type_match or not label_match:
                return markdown
            canvas = self._chart(type_match.group(1), label_match.group(1), markup)
            markdown = before.rstrip() + "\n" + canvas + "\n" + after.lstrip()

    def _chart(self, chart_type: str, labels: str, markup: str) -> str:
        # `useThemeColors` reads CSS variables from the DOM upstream (getComputedStyle), which
        # has no equivalent at build time, so the default palette is always used.
        chart: dict = {
            "data": {"datasets": [], "labels": _parse_labels(labels)},
            "options": {"elements": {}},
        }
        for i, m in enumerate(self._dataset.finditer(markup)):
            dataset: dict = {"data": _js_json(m.group(2)), "label": m.group(1)}
            if i < len(_CHART_COLORS):
                dataset["backgroundColor"] = _CHART_COLORS[i]
            chart["data"]["datasets"].append(dataset)

        options = chart["options"]
        options["elements"][chart_type] = {}
        s = self._settings
        if m := s["spanGaps"].search(markup):
            options["elements"][chart_type][m.group(1)] = _js_json(m.group(2))
        if m := s["tension"].search(markup):
            options["elements"][chart_type][m.group(1)] = _js_json(m.group(2))
        if m := s["beginAtZero"].search(markup):
            options.setdefault("scales", {}).setdefault("y", {})[m.group(1)] = _js_json(m.group(2))
        if m := s["legend"].search(markup):
            options.setdefault("plugins", {}).setdefault("legend", {})["display"] = _js_json(m.group(2))
        if m := s["legendPosition"].search(markup):
            options.setdefault("plugins", {}).setdefault("legend", {})["position"] = m.group(2)
        if m := s["stacked"].search(markup):
            scales = options.setdefault("scales", {})
            scales.setdefault("y", {})
            scales.setdefault("x", {})
            scales["x"][m.group(1)] = _js_json(m.group(2))
            scales["y"][m.group(1)] = _js_json(m.group(2))
        if m := s["height"].search(markup):
            self.ctx.options["height"] = _js_unary_plus(m.group(2))

        height = self.ctx.options.get("height")
        height_str = _format_js_number(height)
        return (
            f'<canvas style="max-height:{height_str}px" data-chart="{chart_type}" >\n'
            f"<!--\n{_json_stringify(chart)}-->\n</canvas>"
        )


def _js_unary_plus(value: str) -> float:
    text = value.strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return math.nan


def _format_js_number(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


def _parse_labels(labels: str) -> list[str]:
    out = []
    for label in labels[1:-1].split(","):
        value = label.strip()
        if value.startswith(("'", '"')):
            value = value[1:]
        if value.endswith(("'", '"')):
            value = value[:-1]
        out.append(value.strip())
    return out
