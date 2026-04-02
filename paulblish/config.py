import tomllib
from pathlib import Path

import frontmatter as fm

from paulblish.models import SiteConfig

REQUIRED_FIELDS = ("title", "base_url", "description", "author")


def _find_home(source_dir: Path) -> Path | None:
    """Find Home.md (case-insensitive) at the source root."""
    for candidate in source_dir.iterdir():
        if candidate.is_file() and candidate.stem.lower() == "home" and candidate.suffix.lower() == ".md":
            return candidate
    return None


def _load_from_toml(toml_path: Path) -> dict:
    """Parse site.toml and return the [site] table as a dict."""
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"Error: Failed to parse {toml_path}\n       {e}") from e

    if "site" not in data:
        raise SystemExit(f"Error: {toml_path} is missing the required [site] table.")

    return data["site"]


def _load_from_home(home_path: Path) -> dict:
    """Parse Home.md frontmatter and return site config fields as a dict."""
    try:
        post = fm.load(home_path)
    except Exception as e:
        raise SystemExit(f"Error: Failed to parse frontmatter in {home_path}\n       {e}") from e

    return dict(post.metadata)


def _validate_and_build(site: dict, source_label: str, **overrides: str) -> SiteConfig:
    """Validate required fields and return a SiteConfig. source_label is used in error messages."""
    for field in REQUIRED_FIELDS:
        if field not in site:
            raise SystemExit(
                f"Error: Missing required config field '{field}' in {source_label}\n"
                f"       Add '{field}' to your site.toml or Home.md frontmatter.\n"
                f"       See: https://github.com/phalt/paulblish#site-configuration"
            )

    for key, value in overrides.items():
        if value is not None:
            site[key] = value

    return SiteConfig(
        title=site["title"],
        base_url=str(site["base_url"]).rstrip("/"),
        description=site["description"],
        author=site["author"],
        cname=site.get("cname", ""),
        avatar=site.get("avatar", ""),
        github=site.get("github", ""),
        bluesky=site.get("bluesky", ""),
        email=site.get("email", ""),
    )


def load_config(source_dir: Path, **overrides: str | None) -> tuple[SiteConfig, str]:
    """Load site config from site.toml or Home.md frontmatter.

    Tries site.toml first. Falls back to Home.md frontmatter if site.toml is absent.
    Exits with code 1 if neither is found or required fields are missing.

    Returns (SiteConfig, source_label) where source_label is the filename used.
    """
    toml_path = source_dir / "site.toml"
    home_path = _find_home(source_dir)

    if toml_path.exists():
        site = _load_from_toml(toml_path)
        return _validate_and_build(site, str(toml_path), **overrides), "site.toml"

    if home_path is not None:
        site = _load_from_home(home_path)
        return _validate_and_build(site, str(home_path), **overrides), home_path.name

    raise SystemExit(
        f"Error: No site configuration found in {source_dir}\n"
        "       Either create a site.toml file or add site config fields to your Home.md frontmatter:\n"
        "\n"
        "         title, base_url, description, author\n"
        "\n"
        "       See: https://github.com/phalt/paulblish#site-configuration"
    )
