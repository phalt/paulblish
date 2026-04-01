from pathlib import Path

import click

from paulblish.config import load_config
from paulblish.renderer import render
from paulblish.scanner import scan
from paulblish.writer import write

VERSION = "0.1.0"


@click.group()
def main():
    """Paulblish — turn your markdown directories into a static site."""


@main.command()
@click.option("--source", "-s", default=".", help="Path to the Obsidian vault directory to scan.")
@click.option("--output", "-o", default="./_site", help="Path to write generated HTML.")
@click.option("--base-url", default=None, help="Base URL for absolute links (overrides site.toml).")
def build(source: str, output: str, base_url: str | None) -> None:
    """Build the static site from a source directory."""
    source_dir = Path(source).resolve()
    output_dir = Path(output).resolve()

    click.echo(f"Paulblish v{VERSION}")
    click.echo(f"Source: {source_dir}")

    # Validate source directory
    if not source_dir.is_dir():
        click.echo(f"\nError: Source directory does not exist: {source_dir}")
        raise SystemExit(1)

    # Load and validate config
    _config = load_config(source_dir, base_url=base_url)  # noqa: F841 — needed for validation, used in later phases
    click.echo("Config: site.toml ✓")

    # Scan
    click.echo("\nScanning...\n")
    articles, skipped = scan(source_dir)

    for article in articles:
        if article.is_home:
            click.echo(f"  ✓ {article.relative_path} → / (index)")
        else:
            click.echo(f"  ✓ {article.relative_path} → {article.url_path}")

    for skip in skipped:
        click.echo(f"  ✗ {skip.path} ({skip.reason})")

    click.echo(f"\nBuilding {len(articles)} articles, skipped {len(skipped)} files\n")

    # Render
    for article in articles:
        render(article)

    # Write
    written = write(articles, output_dir)
    for path in written:
        click.echo(f"  → {path.relative_to(output_dir.parent)}")

    click.echo(f"\nDone. {len(articles)} articles, 0 warnings.")


if __name__ == "__main__":
    main()
