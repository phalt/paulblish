# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
