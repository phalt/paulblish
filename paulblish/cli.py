import time
from pathlib import Path

import click

from paulblish.assets import collect_assets, copy_assets
from paulblish.config import load_config
from paulblish.linker import build_path_map
from paulblish.renderer import render
from paulblish.scanner import scan
from paulblish.writer import write, write_build_meta, write_cname

VERSION = "0.1.0"


@click.group()
def main():
    """Paulblish — turn your markdown directories into a static site."""


@main.command()
@click.option("--source", "-s", default=".", help="Path to the Obsidian vault directory to scan.")
@click.option("--output", "-o", default="./_site", help="Path to write generated HTML.")
@click.option("--base-url", default=None, help="Base URL for absolute links (overrides site.toml).")
@click.option("--templates", default=None, help="Path to custom Jinja2 templates directory.")
@click.option("--drafts", is_flag=True, default=False, help="Include articles without publish: true.")
def build(source: str, output: str, base_url: str | None, templates: str | None, drafts: bool) -> None:
    """Build the static site from a source directory."""
    source_dir = Path(source).resolve()
    output_dir = Path(output).resolve()
    templates_dir = Path(templates).resolve() if templates else None

    click.echo(f"Paulblish v{VERSION}")
    click.echo(f"Source: {source_dir}")

    # Validate source directory
    if not source_dir.is_dir():
        click.echo(f"\nError: Source directory does not exist: {source_dir}")
        raise SystemExit(1)

    # Load and validate config
    config, config_source = load_config(source_dir, base_url=base_url)
    click.echo(f"Config: {config_source} ✓")

    # Scan
    click.echo("\nScanning...\n")
    articles, skipped = scan(source_dir, include_drafts=drafts)

    for article in articles:
        if article.is_home:
            click.echo(f"  ✓ {article.relative_path} → / (index)")
        else:
            click.echo(f"  ✓ {article.relative_path} → {article.url_path}")

    for skip in skipped:
        click.echo(f"  ✗ {skip.path} ({skip.reason})")

    click.echo(f"\nBuilding {len(articles)} articles, skipped {len(skipped)} files\n")

    build_start = time.perf_counter()

    # Build path map for wikilink resolution
    path_map = build_path_map(articles)

    # Render markdown to HTML
    for article in articles:
        render(article, path_map=path_map, base_url=config.base_url)

    # Collect and copy assets
    asset_refs = collect_assets(articles, source_dir, site=config)
    asset_warnings = copy_assets(asset_refs, output_dir)
    for warning in asset_warnings:
        click.echo(f"  ⚠ {warning}")

    # Write templated output
    written = write(articles, output_dir, site=config, templates_dir=templates_dir)
    for path in written:
        click.echo(f"  → {path.relative_to(output_dir.parent)}")

    # Write CNAME if configured
    cname_path = write_cname(output_dir, config.cname)
    if cname_path:
        click.echo(f"  → {cname_path.relative_to(output_dir.parent)}")

    # Write build metadata so pb serve can rewrite base_url for local preview
    write_build_meta(output_dir, config.base_url)

    elapsed = time.perf_counter() - build_start
    num_assets = len([r for r in asset_refs if r.source_path])
    num_warnings = len(asset_warnings)
    warning_str = f", {num_warnings} warning{'s' if num_warnings != 1 else ''}" if num_warnings else ""
    click.echo(f"\nDone. Built {len(articles)} articles, {num_assets} assets{warning_str} in {elapsed:.2f}s.")


@main.command()
@click.option("--output", "-o", default="./_site", help="Path to the built site directory to remove.")
def clean(output: str) -> None:
    """Remove the built site directory."""
    import shutil

    output_dir = Path(output).resolve()

    if not output_dir.exists():
        click.echo(f"Nothing to clean: {output_dir} does not exist.")
        return

    shutil.rmtree(output_dir)
    click.echo(f"Removed {output_dir}")


@main.command()
@click.option("--output", "-o", default="./_site", help="Path to the built site directory.")
@click.option("--port", "-p", default=8000, help="Port to serve on.")
def serve(output: str, port: int) -> None:
    """Serve the built site locally for preview."""
    import functools
    import http.server
    import json

    output_dir = Path(output).resolve()

    if not output_dir.is_dir():
        click.echo(f"Error: Output directory does not exist: {output_dir}")
        click.echo("       Run 'pb build' first.")
        raise SystemExit(1)

    # Read base_url from build metadata so links can be rewritten for local preview
    meta_path = output_dir / ".pb-meta.json"
    rewrite_from = ""
    if meta_path.exists():
        try:
            rewrite_from = json.loads(meta_path.read_text()).get("base_url", "")
        except Exception:
            pass

    if rewrite_from:
        click.echo(f"Rewriting '{rewrite_from}' → '' in HTML/XML responses for local preview.")

    click.echo(f"Serving {output_dir} at http://localhost:{port}")
    click.echo("Press Ctrl+C to stop.\n")

    def _make_handler():
        class RewritingHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if not rewrite_from:
                    super().do_GET()
                    return

                fs_path = Path(self.translate_path(self.path))
                if fs_path.is_dir():
                    fs_path = fs_path / "index.html"

                if not fs_path.is_file() or fs_path.suffix.lower() not in (".html", ".xml"):
                    super().do_GET()
                    return

                content = fs_path.read_bytes().replace(rewrite_from.encode(), b"")
                ctype = "text/html; charset=utf-8" if fs_path.suffix.lower() == ".html" else "application/xml"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        return functools.partial(RewritingHandler, directory=str(output_dir))

    server = http.server.HTTPServer(("localhost", port), _make_handler())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nStopped.")


if __name__ == "__main__":
    main()
