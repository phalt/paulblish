# CLAUDE.md

## Project Overview

Paulblish (`pb`) is a CLI tool that converts an Obsidian vault directory into a static HTML site for GitHub Pages deployment. See `spec.md` for the full specification.

## Reference Project

All structural decisions (layout, tooling, conventions) follow [phalt/clientele](https://github.com/phalt/clientele). When in doubt about "how should this be structured?" — do it the way clientele does it.

## Project Conventions

- **Package layout:** Flat layout with `paulblish/` at repo root (not `src/`).
- **Dependency management:** `uv` for everything. `uv.lock` committed. `.python-version` pinning Python version.
- **Build backend:** `hatchling` in `pyproject.toml`.
- **Linting/formatting:** `ruff` configured in `pyproject.toml` under `[tool.ruff]`. Line length 120, target Python 3.13.
- **Tests:** `pytest` in `tests/` at repo root. Fixtures in `tests/fixtures/`.
- **Makefile:** `make install`, `make test`, `make lint`, `make format`, `make clean`.

## Key Rules

- **Every implementation change must include tests.** Before marking a phase step as done, either confirm existing test coverage is sufficient and adapt it, or write new tests. No untested code gets checked off.

- `_site/` is NOT in `.gitignore` — it is committed and deployed.
- `site.toml` is required in the source directory. Missing = exit code 1 with clear error.
- Articles require `publish: true` in YAML frontmatter to be included.
- Directory structure of the source vault is preserved in output URL paths.
- `Home.md` (case-insensitive) at source root maps to `output/index.html`.
- Templates use `{{ article.body_html | safe }}` — the `| safe` filter is mandatory.
- The `<div class="article-body">` wrapper must not be removed — it's the CSS styling hook.
- CLI output must show every `.md` file as picked up or skipped with reason.

## Development Commands

```bash
make install        # uv sync
make test           # uv run pytest
make lint           # uv run ruff check .
make format         # uv run ruff format .
make clean          # rm -rf _site/ + __pycache__ + egg-info
uv run pb build -s /path/to/vault -o ./_site   # build the site
```

## Implementation Progress

Current phase: **Phase 8 — Extra Features**

After completing each phase action, check it off in `spec.md` (change `- [ ]` to `- [x]`) and update the current phase note here if the phase changes.

## Architecture

Build pipeline sequence: validate source -> validate config -> load config -> scan -> report scan -> build path map -> render -> collect assets -> copy assets -> template -> generate listings -> generate CNAME -> write -> report.

Key modules:

- `cli.py` — click entry point
- `config.py` — SiteConfig loading + site.toml validation
- `models.py` — Article and SiteConfig dataclasses
- `scanner.py` — directory walk, frontmatter parsing, filtering
- `renderer.py` — markdown-it-py setup + plugin chain
- `linker.py` — path lookup table, wikilink resolution
- `assets.py` — asset discovery, copy, path rewriting
- `templating.py` — Jinja2 environment setup + render
- `writer.py` — output directory creation + file writing
- `manifest.py` — incremental build manifest (load/save `.pb-manifest.json`)
