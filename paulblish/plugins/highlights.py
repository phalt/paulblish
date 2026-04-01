import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

_HIGHLIGHT_RE = re.compile(r"==(.+?)==")


def _highlights_inline(state: StateInline, silent: bool) -> bool:
    """Parse ==text== and emit a mark_open / mark_close token pair."""
    if state.src[state.pos : state.pos + 2] != "==":
        return False

    start = state.pos + 2
    end = state.src.find("==", start)
    if end == -1:
        return False

    if not silent:
        open_token = state.push("mark_open", "mark", 1)
        open_token.markup = "=="

        content_token = state.push("text", "", 0)
        content_token.content = state.src[start:end]

        close_token = state.push("mark_close", "mark", -1)
        close_token.markup = "=="

    state.pos = end + 2
    return True


def highlights_plugin(md: MarkdownIt) -> None:
    """Register the ==highlight== → <mark> inline plugin."""
    md.add_render_rule("mark_open", lambda tokens, idx, options, env, self: "<mark>")
    md.add_render_rule("mark_close", lambda tokens, idx, options, env, self: "</mark>")
    md.inline.ruler.push("highlights", _highlights_inline)
