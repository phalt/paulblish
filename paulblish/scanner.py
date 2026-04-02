import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import frontmatter

from paulblish.models import Article

H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class SkippedFile:
    path: Path
    reason: str


def _resolve_slug(metadata: dict) -> str | None:
    """Return slug from frontmatter, using permalink as alias. Returns None if neither exists.

    Leading and trailing slashes are stripped so slugs like '/articles/foo' or 'articles/foo/'
    do not produce double-slashes in URL paths or absolute filesystem paths in the writer.
    """
    slug = metadata.get("slug")
    if slug:
        return str(slug).strip("/")
    permalink = metadata.get("permalink")
    if permalink:
        return str(permalink).strip("/")
    return None


def _resolve_title(metadata: dict, body: str, filename: str) -> str:
    """Resolve title: frontmatter -> first H1 -> deslugified filename."""
    title = metadata.get("title")
    if title:
        return str(title)
    match = H1_RE.search(body)
    if match:
        return match.group(1).strip()
    # Deslugify filename: remove .md, replace hyphens/underscores with spaces, title case
    return filename.removesuffix(".md").replace("-", " ").replace("_", " ").title()


def _resolve_date(metadata: dict, file_path: Path) -> datetime:
    """Resolve date: frontmatter -> file mtime."""
    date = metadata.get("date")
    if date is not None:
        if isinstance(date, datetime):
            return date
        # python-frontmatter parses YAML dates as datetime.date
        return datetime(date.year, date.month, date.day)
    mtime = file_path.stat().st_mtime
    return datetime.fromtimestamp(mtime)


def _is_home(file_path: Path, source_dir: Path) -> bool:
    """Check if file is Home.md (case-insensitive) at source root."""
    return file_path.parent == source_dir and file_path.stem.lower() == "home"


def scan(source_dir: Path, include_drafts: bool = False) -> tuple[list[Article], list[SkippedFile]]:
    """Scan source directory for publishable markdown files.

    Returns (articles, skipped) where articles are valid Article instances
    and skipped contains files that were found but not included, with reasons.
    """
    articles: list[Article] = []
    skipped: list[SkippedFile] = []

    md_files = sorted(source_dir.rglob("*.md"))

    for file_path in md_files:
        relative_path = file_path.relative_to(source_dir)

        # Parse frontmatter
        try:
            post = frontmatter.load(file_path)
        except Exception as e:
            skipped.append(SkippedFile(path=relative_path, reason=f"failed to parse frontmatter: {e}"))
            continue

        metadata = post.metadata

        # Check publish flag — compare by value to handle both bool True and string "true"
        publish = metadata.get("publish", False)
        if not include_drafts and str(publish).lower() != "true":
            skipped.append(SkippedFile(path=relative_path, reason="publish is not true"))
            continue

        # Resolve slug (required)
        slug = _resolve_slug(metadata)
        if slug is None:
            skipped.append(SkippedFile(path=relative_path, reason="missing slug (no slug or permalink in frontmatter)"))
            continue

        # Build path components
        is_home = _is_home(file_path, source_dir)
        path_prefix = str(relative_path.parent) if str(relative_path.parent) != "." else ""

        if is_home:
            url_path = "/"
        elif path_prefix:
            url_path = f"/{path_prefix}/{slug}/"
        else:
            url_path = f"/{slug}/"

        article = Article(
            source_path=file_path,
            relative_path=relative_path,
            path_prefix=path_prefix,
            title=_resolve_title(metadata, post.content, file_path.name),
            slug=slug,
            url_path=url_path,
            date=_resolve_date(metadata, file_path),
            body_markdown=post.content,
            tags=metadata.get("tags") or [],
            description=str(metadata.get("description", "")),
            is_home=is_home,
        )
        articles.append(article)

    return articles, skipped
