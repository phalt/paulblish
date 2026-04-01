"""markdown-it-py plugin for Obsidian-style wikilinks: [[target]] and [[target|alias]]."""

import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def wikilinks_plugin(md: MarkdownIt) -> None:
    """Register the wikilinks inline rule."""
    md.inline.ruler.push("wikilinks", _wikilinks_rule)
    md.add_render_rule("wikilink", _wikilink_render)


def _normalise(name: str) -> str:
    """Normalise a wikilink target for path map lookup."""
    name = name.strip()
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name.lower()


def _wikilinks_rule(state: StateInline, silent: bool) -> bool:
    """Parse [[target]] and [[target|alias]] wikilink syntax."""
    if state.src[state.pos : state.pos + 2] != "[[":
        return False

    # Find the closing ]]
    match = WIKILINK_RE.match(state.src[state.pos :])
    if not match:
        return False

    if not silent:
        token = state.push("wikilink", "", 0)
        token.meta = {
            "target": match.group(1).strip(),
            "alias": match.group(2).strip() if match.group(2) else None,
        }

    state.pos += match.end()
    return True


def _wikilink_render(self, tokens, idx, options, env) -> str:
    """Render a wikilink token to HTML, resolving via path_map in env."""
    meta = tokens[idx].meta
    target = meta["target"]
    alias = meta["alias"]
    display = alias if alias else target

    path_map = env.get("path_map", {})
    base_url = env.get("base_url", "")
    normalised = _normalise(target)
    url = path_map.get(normalised)

    if url:
        return f'<a href="{base_url}{url}">{display}</a>'
    return f'<span class="wikilink-dead">{display}</span>'
