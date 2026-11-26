import contextlib
import time
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape

from paulblish.assets import collect_assets, copy_assets
from paulblish.config import load_config
from paulblish.cv.build import CV_LAYOUT, NotACVError, cv_from_article, load_cv, pdf_output_path, render_cv, write_pdf
from paulblish.linker import build_path_map
from paulblish.manifest import (
    load_manifest,
    load_manifest_excerpts,
    load_manifest_outputs,
    load_manifest_pdfs,
    save_manifest,
)
from paulblish.renderer import render
from paulblish.scanner import scan
from paulblish.slides.build import (
    AssetRegistry,
    VaultIndex,
    add_decks_to_path_map,
    find_slides_dir,
    render_deck,
    scan_decks,
)
from paulblish.templating import PELE_URL
from paulblish.writer import write, write_build_meta, write_cname

VERSION = "0.1.0"

PICKED = "[bold green]✓[/]"
SKIPPED = "[bold red]✗[/]"
WARNING = "[bold yellow]⚠[/]"
WRITTEN = "[magenta]→[/]"


def _console() -> Console:
    # Built per command so it binds to the current stdout (CliRunner swaps it in tests).
    # Rich drops colour by itself when stdout isn't a terminal or NO_COLOR is set.
    return Console(highlight=False, soft_wrap=True)


def _error(console: Console, message: str) -> None:
    lines = message.removeprefix("Error: ").splitlines()
    console.print(f"\n[bold red]Error:[/] [red]{escape(lines[0])}[/]")
    for line in lines[1:]:
        console.print(f"       {escape(line.strip())}")


@click.group()
def main():
    """Paulblish — turn your markdown directories into a static site."""


@main.command()
@click.option("--source", "-s", default=".", help="Path to the Obsidian vault directory to scan.")
@click.option("--output", "-o", default="./_site", help="Path to write generated HTML.")
@click.option("--base-url", default=None, help="Base URL for absolute links (overrides site.toml).")
@click.option("--templates", default=None, help="Path to custom Jinja2 templates directory.")
@click.option("--drafts", is_flag=True, default=False, help="Include articles without publish: true.")
@click.option("--incremental", is_flag=True, default=False, help="Skip articles unchanged since last build.")
def build(
    source: str, output: str, base_url: str | None, templates: str | None, drafts: bool, incremental: bool
) -> None:
    """Build the static site from a source directory."""
    source_dir = Path(source).resolve()
    output_dir = Path(output).resolve()
    templates_dir = Path(templates).resolve() if templates else None

    console = _console()
    console.print(f"[bold magenta]Paulblish[/] [dim]v{VERSION}[/]")
    console.print(f"[cyan]Source:[/] {escape(str(source_dir))}")

    # Validate source directory
    if not source_dir.is_dir():
        _error(console, f"Source directory does not exist: {source_dir}")
        raise SystemExit(1)

    # Load and validate config
    try:
        config, config_source = load_config(source_dir, base_url=base_url)
    except SystemExit as e:
        if not isinstance(e.code, str):
            raise
        _error(console, e.code)
        raise SystemExit(1) from None
    console.print(f"[cyan]Config:[/] {escape(config_source)} {PICKED}")

    # Load manifest for incremental builds (empty dicts if doing a full build)
    manifest: dict[str, float] = load_manifest(output_dir) if incremental else {}
    manifest_outputs: dict[str, str] = load_manifest_outputs(output_dir) if incremental else {}
    manifest_pdfs: dict[str, str] = load_manifest_pdfs(output_dir) if incremental else {}
    manifest_excerpts: dict[str, str] = load_manifest_excerpts(output_dir) if incremental else {}

    # Scan (the slides directory holds decks, not articles)
    console.print("\n[bold cyan]Scanning...[/]\n")
    slides_dir = find_slides_dir(source_dir, config.slides_directory)
    articles, skipped = scan(source_dir, include_drafts=drafts, exclude_dir=slides_dir)
    decks, deck_skipped = scan_decks(slides_dir, source_dir, include_drafts=drafts) if slides_dir else ([], [])
    slides_prefix = slides_dir.relative_to(source_dir).as_posix().lower() if slides_dir else None
    if decks:
        config.slides_url = f"/{slides_prefix}/"

    # Determine stale / fresh sets for incremental mode
    if incremental:
        stale_set: set[int] = set()
        fresh_set: set[int] = set()
        for article in articles:
            key = str(article.relative_path)
            if key not in manifest or article.source_path.stat().st_mtime > manifest[key]:
                stale_set.add(id(article))
            else:
                fresh_set.add(id(article))

        # Delete HTML, a CV's PDF (it has the phone number) and empty parent dirs for files absent from the vault
        current_keys = {str(a.relative_path) for a in articles}
        for absent_key, out_rel in manifest_outputs.items():
            if absent_key not in current_keys:
                for rel in filter(None, (out_rel, manifest_pdfs.get(absent_key))):
                    out_file = output_dir / rel
                    if out_file.exists():
                        out_file.unlink()
                        parent = out_file.parent
                        if parent != output_dir and not any(parent.iterdir()):
                            parent.rmdir()
                console.print(f"  {SKIPPED} {escape(absent_key)} [dim](removed from output)[/]")

        # Restore feed excerpts for fresh articles (body_html is "" because they weren't rendered)
        for article in articles:
            if id(article) in fresh_set and not article.description:
                key = str(article.relative_path)
                if key in manifest_excerpts:
                    article.description = manifest_excerpts[key]

        articles_to_write = [a for a in articles if id(a) in stale_set]
    else:
        stale_set = {id(a) for a in articles}
        fresh_set = set()
        articles_to_write = None  # write() will use the full list

    # Print scan results
    for article in articles:
        if id(article) in fresh_set:
            label = "[dim](unchanged)[/]"
        elif incremental:
            label = "[yellow]→ rebuilt[/]"
        elif article.layout == CV_LAYOUT:
            label = f"[cyan]→ {escape(article.url_path)} (cv)[/]"
        elif article.is_home:
            label = "[cyan]→ / (index)[/]"
        else:
            label = f"[cyan]→ {escape(article.url_path)}[/]"
        console.print(f"  {PICKED} [bold]{escape(str(article.relative_path))}[/] {label}")

    for deck in decks:
        console.print(
            f"  {PICKED} [bold]{escape(str(deck.relative_path))}[/] [cyan]→ {escape(deck.url_path)} (slides)[/]"
        )

    for skip in [*skipped, *deck_skipped]:
        console.print(f"  {SKIPPED} {escape(str(skip.path))} [dim]({escape(skip.reason)})[/]")

    # CVs stay in `articles` above so freshness, wikilinks and the manifest treat them like any page
    pages = [a for a in articles if a.layout != CV_LAYOUT]
    cv_pairs = [(a, cv_from_article(a)) for a in articles if a.layout == CV_LAYOUT]
    cvs = [cv for _, cv in cv_pairs]
    cvs_to_write = [cv for a, cv in cv_pairs if id(a) in stale_set]
    if articles_to_write is not None:
        articles_to_write = [a for a in articles_to_write if a.layout != CV_LAYOUT]

    rebuild_count = sum(id(a) in stale_set for a in pages)
    num_skipped = len(skipped) + len(deck_skipped)
    deck_str = f", [green]{len(decks)}[/] slide deck{'s' if len(decks) != 1 else ''}" if decks else ""
    cv_str = f", [green]{len(cvs_to_write)}[/] CV{'s' if len(cvs_to_write) != 1 else ''}" if cvs else ""
    console.print(
        f"\n[bold]Building [green]{rebuild_count}[/] articles{deck_str}{cv_str}, "
        f"skipped [red]{num_skipped}[/] files[/]\n"
    )

    build_start = time.perf_counter()

    # Build path map for wikilink resolution (always uses full article list, plus decks)
    path_map = build_path_map(articles)
    add_decks_to_path_map(path_map, decks)

    # Render markdown to HTML — only stale articles in incremental mode
    for article in articles_to_write if articles_to_write is not None else pages:
        render(article, path_map=path_map, base_url=config.base_url)
    cv_warnings: list[str] = []
    for cv in cvs_to_write:
        cv_warnings += render_cv(cv, path_map=path_map, base_url=config.base_url)

    # Collect and copy assets for ALL articles and CVs (fresh articles may reference assets)
    asset_refs = collect_assets(articles, source_dir, site=config)

    # Render slide decks; files they reference join the article assets in /assets/
    registry = AssetRegistry(asset_refs)
    deck_warnings: list[str] = []
    if decks:
        index = VaultIndex(source_dir, exclude=output_dir)
        for deck in list(decks):
            try:
                deck_warnings += render_deck(deck, config, index, registry, path_map, PELE_URL, templates_dir)
            except Exception as e:  # a malformed deck (e.g. bad chart data) must not stop the build
                decks.remove(deck)
                deck_warnings.append(f"{deck.relative_path}: deck not built: {e}")
        if not decks:
            config.slides_url = ""

    asset_warnings = copy_assets(asset_refs + registry.new_refs, output_dir) + deck_warnings + cv_warnings
    for warning in asset_warnings:
        console.print(f"  {WARNING} [yellow]{escape(warning)}[/]")

    # Write templated output
    written = write(
        pages,
        output_dir,
        site=config,
        templates_dir=templates_dir,
        articles_to_write=articles_to_write,
        decks=decks,
        slides_prefix=slides_prefix,
        cvs=cvs,
        cvs_to_write=cvs_to_write,
    )
    for path in written:
        console.print(f"  {WRITTEN} [dim]{escape(str(path.relative_to(output_dir.parent)))}[/]")

    # Write CNAME if configured
    cname_path = write_cname(output_dir, config.cname)
    if cname_path:
        console.print(f"  {WRITTEN} [dim]{escape(str(cname_path.relative_to(output_dir.parent)))}[/]")

    # Write build metadata so pb serve can rewrite base_url for local preview
    write_build_meta(output_dir, config.base_url)

    # Save manifest after every build (full or incremental)
    pdfs = {str(a.relative_path): pdf_output_path(cv, output_dir) for a, cv in cv_pairs}
    save_manifest(output_dir, articles, pdfs=pdfs)

    elapsed = time.perf_counter() - build_start
    num_assets = len([r for r in asset_refs + registry.new_refs if r.source_path])
    num_warnings = len(asset_warnings)
    warning_str = f", [yellow]{num_warnings} warning{'s' if num_warnings != 1 else ''}[/]" if num_warnings else ""
    decks_done = f", [bold]{len(decks)}[/] slide deck{'s' if len(decks) != 1 else ''}" if decks else ""
    cvs_done = f", [bold]{len(cvs_to_write)}[/] CV{'s' if len(cvs_to_write) != 1 else ''}" if cvs else ""
    console.print(
        f"\n[bold green]Done.[/] Built [bold]{rebuild_count}[/] articles{decks_done}{cvs_done}, "
        f"[bold]{num_assets}[/] assets{warning_str} in [cyan]{elapsed:.2f}s[/]."
    )


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", "-o", default=".", help="Directory to write the PDF to.")
@click.option("--templates", default=None, help="Path to custom Jinja2 templates directory.")
def pdf(file: Path, output: str, templates: str | None) -> None:
    """Render one CV (layout: cv) to PDF, whether or not it is published. Needs no site.toml."""
    console = _console()
    try:
        cv = load_cv(file.resolve())
    except NotACVError as e:
        _error(console, str(e))
        raise SystemExit(1) from None

    # No site to link to, so wikilinks render as plain text
    for warning in render_cv(cv):
        console.print(f"  {WARNING} [yellow]{escape(warning)}[/]")
    templates_dir = Path(templates).resolve() if templates else None
    path = write_pdf(cv, Path(output).resolve() / cv.pdf_name, templates_dir=templates_dir)
    console.print(f"  {WRITTEN} [dim]{escape(str(path))}[/]")


@main.command()
@click.option("--output", "-o", default="./_site", help="Path to the built site directory to remove.")
def clean(output: str) -> None:
    """Remove the built site directory."""
    import shutil

    console = _console()
    output_dir = Path(output).resolve()

    if not output_dir.exists():
        console.print(f"[dim]Nothing to clean: {escape(str(output_dir))} does not exist.[/]")
        return

    shutil.rmtree(output_dir)
    console.print(f"[bold green]Removed[/] {escape(str(output_dir))}")


@main.command()
@click.option("--output", "-o", default="./_site", help="Path to the built site directory.")
@click.option("--port", "-p", default=8000, help="Port to serve on.")
def serve(output: str, port: int) -> None:
    """Serve the built site locally for preview."""
    import functools
    import http.server
    import json

    console = _console()
    output_dir = Path(output).resolve()

    if not output_dir.is_dir():
        _error(console, f"Output directory does not exist: {output_dir}\nRun 'pb build' first.")
        raise SystemExit(1)

    # Read base_url from build metadata so links can be rewritten for local preview
    meta_path = output_dir / ".pb-meta.json"
    rewrite_from = ""
    if meta_path.exists():
        with contextlib.suppress(Exception):
            rewrite_from = json.loads(meta_path.read_text()).get("base_url", "")

    if rewrite_from:
        console.print(f"[dim]Rewriting '{escape(rewrite_from)}' → '' in HTML/XML responses for local preview.[/]")

    console.print(f"[bold green]Serving[/] {escape(str(output_dir))} at [bold cyan]http://localhost:{port}[/]")
    console.print("[dim]Press Ctrl+C to stop.[/]\n")

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
        console.print("\n[yellow]Stopped.[/]")


if __name__ == "__main__":
    main()
