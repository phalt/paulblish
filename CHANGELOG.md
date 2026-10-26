# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Tool widgets for ` ```html embed ` blocks: styled form controls, sliders, meters and progress bars with no classes, plus one-class widgets (`row`, `fields`, `panel`, `switch`, `segmented`, `knob`, `gauge`, `bars`, `stats`, `error`, `live`). Pages with an embed load a small helper script that fills slider tracks, updates `output.live` readouts and makes `knob` dials draggable. See `tests/fixtures/tool_widgets.md` for every widget and the HTML to write. Embeds and widgets work in any markdown file, including `Home.md`.

### Changed

- `pb build`, `pb clean` and `pb serve` output is coloured with [Rich](https://github.com/Textualize/rich): green ✓, red ✗, yellow warnings, red errors. Piped output and `NO_COLOR` stay plain text.

### Fixed

- RSS excerpts no longer include JavaScript or CSS source from embedded tools.
- Wikilinks resolve by filename as well as frontmatter `title`, so `[[Tools Widgets]]` finds a note titled "Tool widgets". Links between articles and tools now work in both directions.

- Mermaid diagrams are rendered with [Pele](https://pele.run) instead of mermaid.js. Pele is roughly a seventh of the download, lays diagrams out to fit narrow screens, adds zoom for large diagrams, and is themed from the site palette via CSS variables. The version is pinned in `paulblish/templating.py` (`PELE_VERSION`).

## [0.1.0] - Unreleased

### Added

- `pb build` command — converts a markdown directory into a static HTML site.
  - Recursive directory walk with frontmatter parsing (`python-frontmatter`).
  - `publish: true` gating; files without it are skipped and reported.
  - Directory-preserving URL paths (e.g. `articles/foo.md` → `/articles/foo/`).
  - `Home.md` (case-insensitive) maps to the site index (`/`).
  - Wikilink resolution (`[[note]]` and `[[note|alias]]`) with dead-link handling.
  - Obsidian embed syntax (`![[image.png]]`) rewritten to `<img>` tags.
  - Callout blocks, `==highlight==` marks, footnotes, and Mermaid diagrams.
  - Jinja2 templating with cyberpunk / brutalist aesthetic (muted CP2077 palette).
  - Home page with ASCII art banner and optional avatar image.
  - All-pages listing grouped by directory prefix (`/all/`).
  - Tag index pages (`/tags/{tag}/index.html`) for each unique tag.
  - Asset discovery, collision-safe copying, and HTML path rewriting.
  - `CNAME` file generation when `site.cname` is configured.
  - `--drafts` flag to include unpublished articles in the build.
  - `--base-url` and `--templates` CLI overrides.
  - Build stats and elapsed time in final output line.
- `pb clean` command — removes the output directory.
- `pb serve` command — serves the built site locally for preview.
- `site.toml` configuration with `title`, `base_url`, `description`, `author`, `cname`, `avatar`.
- GitHub Actions workflows: `deploy.yml` (push-to-Pages) and `test.yml` (lint + test on PRs).
- Default cyberpunk templates and `style.css`.
- `--incremental` flag for `pb build` — skips re-rendering articles unchanged since the last build; deleted source files have their output HTML removed automatically; a `.pb-manifest.json` manifest is written to the output directory on every build.
