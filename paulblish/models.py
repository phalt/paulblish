from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Article:
    source_path: Path
    relative_path: Path
    path_prefix: str
    title: str
    slug: str
    url_path: str
    date: datetime
    body_markdown: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    body_html: str = ""
    is_home: bool = False
    reading_time_minutes: int = 0
    assets: list[Path] = field(default_factory=list)
    prev_article: Article | None = field(default=None)
    next_article: Article | None = field(default=None)


@dataclass
class SiteConfig:
    title: str
    base_url: str
    description: str
    author: str
    cname: str = ""
    avatar: str = ""
    github: str = ""
    bluesky: str = ""
    email: str = ""
