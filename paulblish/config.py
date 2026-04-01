import tomllib
from pathlib import Path

from paulblish.models import SiteConfig

REQUIRED_FIELDS = ("title", "base_url", "description", "author")


def load_config(source_dir: Path, **overrides: str) -> SiteConfig:
    """Load and validate site.toml from the source directory. Returns a SiteConfig."""
    toml_path = source_dir / "site.toml"

    if not toml_path.exists():
        raise SystemExit(
            f"Error: No site.toml found in {source_dir}\n"
            "       Every source directory must contain a site.toml file.\n"
            "       See: https://github.com/phalt/paulblish#site-configuration"
        )

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"Error: Failed to parse {toml_path}\n       {e}") from e

    if "site" not in data:
        raise SystemExit(f"Error: {toml_path} is missing the required [site] table.")

    site = data["site"]

    for field in REQUIRED_FIELDS:
        if field not in site:
            raise SystemExit(f"Error: {toml_path} is missing required field 'site.{field}'.")

    # Apply CLI overrides
    for key, value in overrides.items():
        if value is not None:
            site[key] = value

    return SiteConfig(
        title=site["title"],
        base_url=site["base_url"],
        description=site["description"],
        author=site["author"],
        cname=site.get("cname", ""),
        avatar=site.get("avatar", ""),
    )
