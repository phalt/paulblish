# Paulblish 📖

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI tool that converts an Obsidian vault (or any directory of markdown files) into a static HTML site with a cyberpunk aesthetic, ready for deployment to GitHub Pages.

## What is this?

Paulblish (`pb`) takes a directory of markdown files — such as an [Obsidian](https://obsidian.md) vault — and generates a complete static HTML site from it. The generated output is committed directly to the repo and deployed via GitHub Pages. Your source vault lives on your machine; only the HTML output is in version control.

The project follows the [file over app](https://stephango.com/file-over-app) philosophy. Your content stays in plain markdown, and the site generator is just a tool you run locally.

## Quick Start

```sh
git clone https://github.com/phalt/paulblish.git
cd paulblish
make install
uv run pb build --source ~/obsidian/blog --output ./_site
git add _site/
git commit -m "Rebuild site"
git push
```

## Installation

Clone the repo and install dependencies using `uv`:

```sh
git clone https://github.com/phalt/paulblish.git
cd paulblish
make install
```

## Usage

### `pb build`

Build the static site from a source directory.

```sh
uv run pb build --source ~/obsidian/blog --output ./_site
```

| Flag | Default | Description |
| --- | --- | --- |
| `--source`, `-s` | `.` (cwd) | Path to the markdown source directory. Must contain a `site.toml`. |
| `--output`, `-o` | `./_site` | Path to write generated HTML. |
| `--base-url` | _(from site.toml)_ | Base URL for absolute links (overrides `site.toml`). |
| `--templates` | _(bundled defaults)_ | Path to a custom Jinja2 templates directory. |
| `--drafts` | `false` | Include articles without `publish: true`. |

### `pb clean`

Remove the output directory.

```sh
uv run pb clean --output ./_site
```

| Flag | Default | Description |
| --- | --- | --- |
| `--output`, `-o` | `./_site` | Path to the built site directory to remove. |

### `pb serve`

Serve the built site locally for preview.

```sh
uv run pb serve --output ./_site
uv run pb serve --output ./_site --port 9000
```

| Flag | Default | Description |
| --- | --- | --- |
| `--output`, `-o` | `./_site` | Path to the built site directory to serve. |
| `--port`, `-p` | `8000` | Port to listen on. |

## Site Configuration

Site configuration is loaded from one of two sources, tried in order:

1. **`site.toml`** — a TOML file in the root of your source directory (preferred).
2. **`Home.md` frontmatter** — YAML frontmatter fields in `Home.md` at the source root (useful for Obsidian users where `.toml` files are inconvenient).

If `site.toml` is present it takes priority. If neither source is found, or the required fields are missing, `pb build` exits with an error:

```text
Error: No site configuration found in <source directory>
       Either create a site.toml file or add site config fields to your Home.md frontmatter:

         title, base_url, description, author
```

### Method 1: `site.toml`

Create `site.toml` in the root of your source directory:

```toml
[site]
title       = "My Blog"
base_url    = "https://yourusername.github.io/yourrepo"
description = "A blog about things."
author      = "Your Name"
cname       = ""   # optional — your custom domain, e.g. "blog.example.com"
avatar      = ""   # optional — relative path to a square image for the home page
```

### Method 2: `Home.md` frontmatter

Add the config fields to the YAML frontmatter of your `Home.md`:

```yaml
---
publish: true
title: "My Blog"
base_url: "https://yourusername.github.io/yourrepo"
description: "A blog about things."
author: "Your Name"
cname: ""    # optional
avatar: ""   # optional
---
```

### Fields

| Field | Required | Description |
| --- | --- | --- |
| `title` | yes | Site title shown in `<title>` and the nav bar |
| `base_url` | yes | Absolute base URL (e.g. `https://user.github.io/repo`) |
| `description` | yes | Short site description for `<meta>` tags |
| `author` | yes | Author name shown in footer and meta |
| `cname` | no | Custom domain — writes a `CNAME` file to the output root |
| `avatar` | no | Path to a square image shown on the home page |

## Frontmatter Schema

Only files with `publish: true` in their frontmatter are included in the build.

```yaml
---
publish: true                    # required — must be true to be included
title: "Article Title"           # optional — derived from first H1 or filename if absent
slug: "article-title"            # required — used as the URL segment; also accepts `permalink`
date: 2026-03-15                 # optional — used for sorting; falls back to file mtime
tags: [python, tooling]          # optional — list of strings; generates /tags/{tag}/ pages
description: "A short summary."  # optional — shown in article header and listings
---
```

Files missing a `slug` (or `permalink`) are skipped with a clear reason in the build output.

## Directory Structure

The source directory path of each file is preserved in the output URL:

| Source file | Output path | URL |
| --- | --- | --- |
| `foo.md` | `_site/foo/index.html` | `/foo/` |
| `articles/foo.md` | `_site/articles/foo/index.html` | `/articles/foo/` |
| `articles/deep/bar.md` | `_site/articles/deep/bar/index.html` | `/articles/deep/bar/` |
| `Home.md` | `_site/index.html` | `/` |

## The Home File

A file named `Home.md` (case-insensitive) at the root of your source directory becomes the site index page at `/`.

The home page renders with:

- An ASCII art "Hello" banner (`<pre class="ascii-banner" aria-hidden="true">`)
- An optional avatar image (configured via `site.avatar` in `site.toml`)
- The body content of `Home.md`

If no `Home.md` is present or it is not published, the index page falls back to a generated article listing.

## Deployment

The deployment workflow is: **build locally → commit `_site/` → push → GitHub Actions deploys**.

There is no build step in CI. You build the site on your machine and commit the generated HTML.

### Steps

1. Build the site locally:

   ```sh
   uv run pb build --source ~/obsidian/blog --output ./_site
   ```

2. Commit the output:

   ```sh
   git add _site/
   git commit -m "Rebuild site"
   git push
   ```

3. In your GitHub repo settings, go to **Settings → Pages** and set the source to **GitHub Actions**.

The included `deploy.yml` workflow triggers on any push to `main` that touches `_site/**` and deploys the directory to GitHub Pages.

### Custom Domain

Set `cname` in your `site.toml`:

```toml
cname = "blog.example.com"
```

This writes a `CNAME` file to `_site/CNAME` on every build. GitHub Pages reads the CNAME from the published directory root — no manual setup needed beyond pointing your DNS.

## Development

```sh
make install    # uv sync — install all dependencies
make test       # uv run pytest
make lint       # uv run ruff check .
make format     # uv run ruff format .
make clean      # remove _site/, __pycache__, and egg-info
```

## Fork Your Own Copy

Paulblish is designed so anyone can fork it and run their own blog. To set up your own:

1. Fork this repository (or use "Use this template" on GitHub).
2. Clone it locally and run `make install`.
3. Configure your site — pick whichever suits your workflow:

   **Option A — `site.toml`** (create in the root of your Obsidian directory):

   ```toml
   [site]
   title = "My Blog"
   base_url = "https://yourusername.github.io/yourrepo"
   description = "A blog about things."
   author = "Your Name"
   cname = ""   # set to your custom domain, or leave empty
   avatar = ""  # path to a square image, or leave empty
   ```

   **Option B — `Home.md` frontmatter** (add fields to your existing `Home.md`):

   ```yaml
   ---
   publish: true
   title: "My Blog"
   base_url: "https://yourusername.github.io/yourrepo"
   description: "A blog about things."
   author: "Your Name"
   ---
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
