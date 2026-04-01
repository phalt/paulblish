"""markdown-it-py plugin for Obsidian-style image embeds: ![[image.png]]."""

import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}
EMBED_RE = re.compile(r"!\[\[([^\]]+?)\]\]")


def embeds_plugin(md: MarkdownIt) -> None:
    """Register the image embed inline rule."""
    md.inline.ruler.push("embeds", _embeds_rule)
    md.add_render_rule("image_embed", _embed_render)


def _embeds_rule(state: StateInline, silent: bool) -> bool:
    """Parse ![[filename]] image embed syntax."""
    if state.src[state.pos : state.pos + 3] != "![[":
        return False

    match = EMBED_RE.match(state.src[state.pos :])
    if not match:
        return False

    filename = match.group(1).strip()

    # Only handle image files; skip note embeds (P1)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in IMAGE_EXTENSIONS:
        return False

    if not silent:
        token = state.push("image_embed", "", 0)
        token.meta = {"filename": filename}

    state.pos += match.end()
    return True


def _embed_render(self, tokens, idx, options, env) -> str:
    """Render an image embed token to an <img> tag."""
    filename = tokens[idx].meta["filename"]
    base_url = env.get("base_url", "")
    return f'<img src="{base_url}/assets/{filename}" alt="{filename}">'
