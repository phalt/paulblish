"""Build manifest — tracks source file mtimes and output paths for incremental builds."""

import json
from pathlib import Path

from paulblish.models import Article

MANIFEST_FILE = ".pb-manifest.json"


def _manifest_path(output_dir: Path) -> Path:
    return output_dir / MANIFEST_FILE


def _read_raw(output_dir: Path) -> dict:
    path = _manifest_path(output_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        return {}


def load_manifest(output_dir: Path) -> dict[str, float]:
    """Read .pb-manifest.json and return {relative_source_path: mtime}.

    Returns an empty dict if the file is missing or contains invalid JSON.
    Both the new rich format ({"mtime": float, "output": str}) and the legacy
    plain-float format are accepted.
    """
    raw = _read_raw(output_dir)
    result: dict[str, float] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = float(v.get("mtime", 0.0))
        elif isinstance(v, (int, float)):
            result[k] = float(v)
    return result


def load_manifest_outputs(output_dir: Path) -> dict[str, str]:
    """Return {relative_source_path: relative_output_path} from the manifest.

    Used to locate and delete HTML files for articles that have been removed
    from the source vault since the last build.  Returns only entries that
    contain an "output" key (i.e. written by the current manifest format).
    """
    raw = _read_raw(output_dir)
    return {k: v["output"] for k, v in raw.items() if isinstance(v, dict) and v.get("output")}


def load_manifest_excerpts(output_dir: Path) -> dict[str, str]:
    """Return {relative_source_path: feed_excerpt} from the manifest.

    Used in incremental builds to restore the feed description for fresh articles
    that are not re-rendered (and therefore have body_html == "").
    """
    raw = _read_raw(output_dir)
    return {k: v["excerpt"] for k, v in raw.items() if isinstance(v, dict) and "excerpt" in v}


def _resolve_excerpt(article: Article) -> str:
    """Return the resolved feed description: frontmatter description or plain-text excerpt.

    Mirrors feed._item_description but lives here so the manifest can store it
    without importing from feed.py.
    """
    import re

    if article.description:
        return article.description
    # Strip HTML tags, collapse whitespace, truncate at 200 chars
    text = re.sub(r"<[^>]+>", " ", article.body_html)
    text = " ".join(text.split())
    if len(text) <= 200:
        return text
    truncated = text[:200]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"


def save_manifest(output_dir: Path, articles: list[Article]) -> None:
    """Write .pb-manifest.json mapping each article's relative source path to its
    current mtime, computed output path, and resolved feed excerpt.

    Called at the end of every full or incremental build so the next incremental
    build can determine which articles are fresh and restore their feed descriptions.
    """
    from paulblish.writer import output_path as compute_output_path

    data: dict[str, dict] = {}
    for article in articles:
        rel_key = str(article.relative_path)
        mtime = article.source_path.stat().st_mtime
        out_path = compute_output_path(article, output_dir)
        out_rel = str(out_path.relative_to(output_dir))
        data[rel_key] = {"mtime": mtime, "output": out_rel, "excerpt": _resolve_excerpt(article)}

    output_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(output_dir).write_text(json.dumps(data, indent=2))
