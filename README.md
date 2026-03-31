# Paulblish

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A static site generator that turns a directory of markdown files into a static HTML site, suitable for deployment to GitHub Pages.

The project follows the [file over app](https://stephango.com/file-over-app) philosophy and you can take any markdown formatted directory (such as one for [Obsidian](https://obsidian.md)) and publish a static html site from it.

Paulblish reads the directory, generates a static site from it and outputs HTML that you commit and push to deploy.

## Quick Start

```bash
git clone https://github.com/phalt/paulblish.git
cd paulblish
make install
uv run pb build --source ~/obsidian/blog --output ./_site
git add _site/
git commit -m "Rebuild site"
git push
```

## Installation

```bash
git clone https://github.com/phalt/paulblish.git
cd paulblish
make install
```

## Usage

### `pb build`

Build the static site from an Obsidian vault directory.

```bash
uv run pb build --source ~/obsidian/blog --output ./_site
```

| Flag | Default | Description |
|---|---|---|
| `--source`, `-s` | `.` (cwd) | Path to the Obsidian vault directory to scan. Must contain a `site.toml`. |
| `--output`, `-o` | `./_site` | Path to write generated HTML. |
| `--base-url` | `/` | Base URL for absolute links (overrides `site.toml`). |
| `--templates` | bundled defaults | Path to custom Jinja2 templates directory. |
| `--clean` | `false` | Delete output directory before building. |
| `--drafts` | `false` | Include articles with `publish: false`. |
| `--verbose`, `-v` | `false` | Verbose logging. |

### `pb clean`

Remove the output directory.

```bash
uv run pb clean --output ./_site
```

## Site Configuration

Every source directory must contain a `site.toml` file:

```toml
[site]
title = "My Blog"
base_url = "https://username.github.io/blog"
description = "A blog about things."
author = "Paul"
cname = ""       # optional — custom domain, e.g. "blog.example.com"
avatar = ""      # optional — path to a square image for the home page
```

If `site.toml` is missing, `pb build` exits with an error.

If `cname` is set, a `CNAME` file is written to the output root for GitHub Pages custom domain support.

## Frontmatter Schema

Markdown files require YAML frontmatter with `publish: true` to be included:

```yaml
---
publish: true                    # required — must be true
title: "Article Title"           # optional — derived from H1 or filename if absent
slug: "article-title"            # optional — derived from filename if absent
date: 2026-03-15                 # optional — used for sorting, falls back to file mtime
tags: [python, tooling]          # optional — list of strings
description: "A short summary."  # optional — used in <meta> and listing page
---
```

## Directory Structure

Source directory paths are preserved in output URLs:

| Source file | Output path | URL |
|---|---|---|
| `foo.md` | `_site/foo/index.html` | `/foo/` |
| `articles/foo.md` | `_site/articles/foo/index.html` | `/articles/foo/` |
| `articles/deep/bar.md` | `_site/articles/deep/bar/index.html` | `/articles/deep/bar/` |

## The Home File

A file named `Home.md` (case-insensitive) at the root of the source directory becomes the site index page at `/`. If absent or unpublished, the index falls back to a generated article listing.

The home page displays an ASCII art "Hello" banner and an optional author avatar (configured via `site.avatar` in `site.toml`).

## Deployment

1. Build locally: `uv run pb build --source ~/obsidian/blog --output ./_site`
2. Commit the `_site/` directory.
3. Push to `main` — GitHub Actions deploys the pre-built files.

In your GitHub repo settings, enable Pages and set it to deploy from **GitHub Actions**.

For a custom domain, set `cname` in your `site.toml`.

## Development

```bash
make install    # install dependencies
make test       # run tests
make lint       # run linter
make format     # format code
make clean      # clean build artifacts
```

## Fork Your Own Copy

Paulblish is designed so anyone can fork it and run their own blog. To set up your own:

1. Fork this repository (or use "Use this template" on GitHub).
2. Clone it locally and run `make install`.
3. Create a `site.toml` in the root of your Obsidian content directory:

   ```toml
   [site]
   title = "My Blog"
   base_url = "https://yourusername.github.io/yourrepo"
   description = "A blog about things."
   author = "Your Name"
   cname = ""                      # set to your custom domain, or leave empty
   avatar = ""                     # path to a square image, or leave empty
   ```

4. Ensure your markdown files have `publish: true` in their frontmatter.
5. Create a `Home.md` in the root of your content directory for your index page.
6. Build the site:

   ```sh
   uv run pb build --source /path/to/your/obsidian/dir --output ./_site
   ```

7. Commit the `_site/` directory and push to `main`.
8. In your GitHub repo settings, enable Pages and set it to deploy from GitHub Actions.

The `pb` tool, templates, and styles are all included in the repo. Customise the templates in `templates/` and the CSS in `templates/static/style.css` to make it your own.
