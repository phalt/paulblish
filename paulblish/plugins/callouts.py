import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

_CALLOUT_RE = re.compile(r"^\[!(\w+)\]([+-]?)(.*)$", re.IGNORECASE)

# Supported callout types and their display labels
_CALLOUT_LABELS = {
    "note": "Note",
    "tip": "Tip",
    "important": "Important",
    "warning": "Warning",
    "caution": "Caution",
    "danger": "Danger",
    "info": "Info",
    "todo": "Todo",
    "success": "Success",
    "question": "Question",
    "failure": "Failure",
    "bug": "Bug",
    "example": "Example",
    "quote": "Quote",
    "abstract": "Abstract",
}


def _find_callout_info(tokens: list[Token], bq_open_idx: int) -> tuple[str, str, str] | None:
    """
    Given a blockquote_open token index, look at the first inline child to check
    if it starts with [!TYPE]. Returns (type, label, fold) or None.

    fold is '+' (collapsible, starts open), '-' (collapsible, starts closed), or '' (static).
    """
    for i in range(bq_open_idx + 1, len(tokens)):
        t = tokens[i]
        if t.type == "blockquote_close":
            break
        if t.type == "inline" and t.children:
            first = t.children[0]
            if first.type == "text":
                m = _CALLOUT_RE.match(first.content.strip())
                if m:
                    callout_type = m.group(1).lower()
                    fold = m.group(2)  # '+', '-', or ''
                    custom_title = m.group(3).strip()
                    label = custom_title if custom_title else _CALLOUT_LABELS.get(callout_type, callout_type.title())
                    return callout_type, label, fold
    return None


def _strip_callout_marker(tokens: list[Token], bq_open_idx: int) -> None:
    """
    Remove the [!TYPE] text node (and following softbreak) from the first
    inline token inside the blockquote at bq_open_idx.
    """
    for i in range(bq_open_idx + 1, len(tokens)):
        t = tokens[i]
        if t.type == "blockquote_close":
            break
        if t.type == "inline" and t.children:
            children = t.children
            if children and children[0].type == "text":
                m = _CALLOUT_RE.match(children[0].content.strip())
                if m:
                    # Drop the marker text node
                    rest = children[1:]
                    # Drop the following softbreak if present
                    if rest and rest[0].type == "softbreak":
                        rest = rest[1:]
                    t.children = rest
            break


def _render_blockquote_open(self, tokens: list[Token], idx: int, options, env) -> str:
    info = _find_callout_info(tokens, idx)
    if info is None:
        return "<blockquote>\n"
    callout_type, label, fold = info
    _strip_callout_marker(tokens, idx)
    collapsible = fold in ("+", "-")
    tokens[idx].meta = {"is_callout": True, "collapsible": collapsible}

    if collapsible:
        open_attr = " open" if fold == "+" else ""
        return (
            f'<div class="callout callout-{callout_type} callout-collapsible" data-callout="{callout_type}">\n'
            f"<details{open_attr}>\n"
            f'<summary class="callout-title"><span class="callout-fold"></span>{label}</summary>\n'
            f'<div class="callout-body">\n'
        )
    return (
        f'<div class="callout callout-{callout_type}" data-callout="{callout_type}">\n'
        f'<div class="callout-title">{label}</div>\n'
        f'<div class="callout-body">\n'
    )


def _render_blockquote_close(self, tokens: list[Token], idx: int, options, env) -> str:
    # Walk back to find the matching open to determine if this was a callout
    depth = 0
    for i in range(idx - 1, -1, -1):
        t = tokens[i]
        if t.type == "blockquote_close":
            depth += 1
        elif t.type == "blockquote_open":
            if depth == 0:
                if t.meta and t.meta.get("is_callout"):
                    if t.meta.get("collapsible"):
                        return "</div>\n</details>\n</div>\n"
                    return "</div>\n</div>\n"
                break
            depth -= 1
    return "</blockquote>\n"


def callouts_plugin(md: MarkdownIt) -> None:
    """Register Obsidian-style callout block rendering."""
    md.add_render_rule("blockquote_open", _render_blockquote_open)
    md.add_render_rule("blockquote_close", _render_blockquote_close)
