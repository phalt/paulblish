# Paulblish: Project Specification

**Paulblish** (`pb`) is a CLI tool that converts an Obsidian vault directory into a static HTML site, suitable for deployment to GitHub Pages. It is, obviously, a pun.

---

## 1. Goals

- Replace Obsidian Publish with a self-hosted, zero-cost alternative.
- Generate standard HTML from Obsidian-flavoured markdown.
- Run as a CLI tool (`pb`) pointed at any directory — no Obsidian dependency at runtime.
- Produce clean, addressable URLs that preserve the source directory structure.
- Support a simple local-build workflow: run `pb build` locally, commit the output, push to deploy.

## 2. Non-Goals

- Live preview or dev server (out of scope for v1; use any static file server).
- Dataview query execution (queries are stripped, not evaluated).
- Theme compatibility with Obsidian community themes.
- WYSIWYG editing or CMS features.
- JavaScript-heavy client-side rendering.
- Running the build in CI — the build runs on the developer's machine.

---

## 3. Reference Project

The project **must** use [phalt/clientele](https://github.com/phalt/clientele) as the structural reference for all decisions about project layout, tooling, and conventions. Specifically:

- **Package layout:** Flat layout with the package directory at the repo root (`paulblish/`), not a `src/` layout.
- **Dependency management:** `uv` for all dependency management. `uv.lock` committed to the repo. `.python-version` file pinning the Python version.
- **Build backend:** `hatchling` as the build backend in `pyproject.toml`.
- **Makefile:** A `Makefile` providing common development tasks (`make install`, `make test`, `make lint`, `make build`, `make clean`, etc.).
- **Linting / formatting:** `ruff` for linting and formatting, configured in `pyproject.toml` under `[tool.ruff]`.
- **Tests:** `tests/` directory at the repo root. `pytest` as the test runner.
- **Documentation files:** `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` at the repo root.
- **CI:** `.github/workflows/` for GitHub Actions.

Any time there is a question about "how should this be structured?" or "which tool should we use?", the answer is: do it the way clientele does it.

---

## 4. Content Model

### 4.1 Article Selection

A markdown file is considered publishable if **all** of the following are true:

1. It lives within the configured source directory (recursive).
2. It has YAML frontmatter containing `publish: true`.
3. It has a `.md` extension.

Files without frontmatter, or with `publish: false` / missing `publish` key, are ignored entirely.

### 4.2 Frontmatter Schema

```yaml
---
publish: true                    # required — boolean, must be true
title: "Article Title"           # optional — derived from H1 or filename if absent
slug: "article-title"            # required — permalink is accepted as an alias
date: 2026-03-15                 # optional — used for sorting, falls back to file mtime
tags: [python, tooling]          # optional — list of strings
description: "A short summary."  # optional — used in <meta> and listing page
---
```

**Resolution order for `title`:**

1. Frontmatter `title`
2. First `# H1` heading in the document body
3. Filename (without `.md`, deslugified)

**Resolution order for `slug`:**

1. Frontmatter `slug`
2. Frontmatter `permalink` (alias for slug)
3. Skip — file is not published (no automatic derivation from filename)

**Resolution order for `date`:**

1. Frontmatter `date`
2. File modification time (`mtime`)

### 4.3 Frontmatter Display on Posts

All resolved frontmatter metadata **must** be rendered visibly on each article page. The article template displays:

- **Title** — as the page `<h1>`.
- **Date** — formatted as a human-readable string (e.g. `15 March 2026`), displayed below the title.
- **Tags** — rendered as a list of styled inline labels, each linking to the corresponding tag index page. Displayed below the date.
- **Description** — if present, rendered as a subtitle/lead paragraph below the title block, before the article body. Also used in `<meta name="description">`.

This metadata block is a distinct visual section at the top of every article, styled consistently via the article template.

### 4.4 Directory-Based Paths

The directory structure of the source vault is **preserved** in the output URL paths. The slug is always relative to the source root.

Examples:

| Source file (relative to `--source`) | Output path | URL |
|---|---|---|
| `foo.md` | `output/foo/index.html` | `/foo/` |
| `articles/foo.md` | `output/articles/foo/index.html` | `/articles/foo/` |
| `articles/deep/bar.md` | `output/articles/deep/bar/index.html` | `/articles/deep/bar/` |
| `Home.md` | `output/index.html` | `/` (special case) |

The slug (from frontmatter `slug` or `permalink`) replaces only the filename portion. The parent directory path is always preserved. This means the `Article` model needs a `path_prefix` field representing the relative directory path.

The `slug` (or its alias `permalink`) replaces only the filename portion; the directory prefix is always preserved. For example, `articles/my-draft.md` with `slug: my-post` produces `/articles/my-post/`.

### 4.5 The Home File

The file named `Home.md` (case-insensitive match) in the **root** of the source directory is treated as the site index page. It is rendered to `output/index.html` instead of `output/home/index.html`.

If `Home.md` has `publish: true`, its content becomes the index page body. If it is absent or unpublished, the index page falls back to a generated article listing sorted by date (newest first).

`Home.md` is still included in the "All Pages" listing (see §6.4).

### 4.6 Article Data Model

```python
@dataclass
class Article:
    source_path: Path              # absolute path to the .md file
    relative_path: Path            # path relative to source root (e.g. articles/foo.md)
    path_prefix: str               # directory portion (e.g. "articles", "articles/deep", or "")
    title: str
    slug: str                      # filename portion only (e.g. "foo")
    url_path: str                  # full URL path (e.g. "/articles/foo/")
    date: datetime
    tags: list[str]
    description: str
    body_markdown: str             # raw markdown, frontmatter stripped
    body_html: str                 # populated after rendering
    is_home: bool                  # true if this is the Home file
    assets: list[Path]             # referenced images/files

@dataclass
class SiteConfig:
    title: str
    base_url: str
    description: str
    author: str
    cname: str                     # custom domain for GitHub Pages, or "" if none
    avatar: str                    # path to square avatar image, or "" if none
```

---

## 5. Obsidian Markdown Processing

### 5.1 Rendering Engine

**`markdown-it-py`** with custom plugins for each Obsidian extension. Plugins are applied as a chain — standard markdown is handled by the base parser; Obsidian-isms are layered on top.

### 5.2 Syntax Support Matrix

| Syntax | Example | Output | Priority |
|---|---|---|---|
| Standard CommonMark | `**bold**`, `[link](url)` | Native `markdown-it-py` | P0 |
| YAML frontmatter | `---\ntitle: ...\n---` | Stripped (parsed separately) | P0 |
| Wikilinks | `[[Note Name]]` | `<a href="/note-name/">Note Name</a>` | P0 |
| Wikilinks with alias | `[[Note Name\|display]]` | `<a href="/note-name/">display</a>` | P0 |
| Image embeds | `![[photo.png]]` | `<img src="/assets/photo.png">` | P0 |
| Note embeds | `![[Other Note]]` | Inline rendered HTML of target note | P1 |
| Callouts | `> [!note] Title` | `<div class="callout callout-note">` | P1 |
| Highlights | `==text==` | `<mark>text</mark>` | P1 |
| Fenced code blocks | ` ```python ` | `<pre><code>` with Pygments highlighting | P0 |
| Mermaid blocks | ` ```mermaid ` | `<pre class="mermaid">` (client-side JS) | P2 |
| LaTeX inline | `$E=mc^2$` | `<span class="math">` (KaTeX client-side) | P2 |
| LaTeX block | `$$\sum_{i=1}^{n}$$` | `<div class="math">` (KaTeX client-side) | P2 |
| Dataview blocks | `dataview ...` | Stripped entirely with optional warning comment | P2 |
| Tags in body | `#sometag` | `<span class="tag">sometag</span>` or stripped | P2 |
| Footnotes | `[^1]` | `<sup>` / `<section class="footnotes">` | P1 |

**Priority key:** P0 = required for v1, P1 = important for usability, P2 = nice-to-have.

### 5.3 Wikilink Resolution

A **path lookup table** is built during the scan phase:

```python
# Maps normalised note name -> url_path for all published articles
path_map: dict[str, str] = {
    "note name": "/articles/note-name/",
    "another post": "/deep/another-post/",
}
```

Resolution rules:

1. Normalise the wikilink target: strip `.md`, lowercase, strip leading/trailing whitespace.
2. Look up in `path_map`.
3. If found → render as `<a href="{url_path}">display text</a>`.
4. If not found (target is unpublished or doesn't exist) → render as `<span class="wikilink-dead">display text</span>` (plain text, no link, visually distinct via CSS).

### 5.4 Syntax Highlighting

Fenced code blocks with a language identifier are highlighted at build time using **Pygments**. The output uses CSS classes (not inline styles) so the colour scheme is controlled by the site stylesheet. The Pygments theme must complement the cyberpunk colour palette (see §6.1).

---

## 6. Theme & Templates

### 6.1 Visual Design: Cyberpunk Brutalist

The site uses a **cyberpunk / brutalist web 2.0** aesthetic inspired by the muted, worn tones of Cyberpunk 2077's UI — Night City grime, not arcade neon. The following design constraints apply:

**Colour palette:**

| Role | Colour | Hex | Usage |
|---|---|---|---|
| Background | Near-black, cool-tinted | `#0a0a0f` | Page background |
| Surface | Dark charcoal | `#14141f` | Code blocks, callout backgrounds, card surfaces |
| Primary text | Soft cool grey | `#b8b8c0` | Body text, readable at length |
| Bright text | Off-white | `#e0dfd5` | Headings, article titles, emphasis |
| Muted teal | Desaturated cyan | `#5e9e91` | Links, primary accent, nav highlights |
| Muted amber | Dusty gold | `#b89c4a` | Tags, secondary accent, hover states |
| Muted rose | Dark crimson | `#7a3b4e` | Dead wikilinks, warnings, error states |
| Border | Dark steel | `#2a2a35` | Dividers, borders, grid lines |
| Subtle highlight | Deep teal | `#1a2a28` | Hover backgrounds, active states |

Accent colours are used sparingly for interactive elements and structural markers — never for body text. The overall feel should evoke dusty neon signage seen through rain, not a rave.

**Typography:**

- Headings and UI elements: monospace font stack (`'JetBrains Mono', 'Fira Code', 'Courier New', monospace`).
- Body text: sans-serif (`'Inter', 'system-ui', sans-serif`). Size 16–18px, line-height 1.6–1.7 for readability.

**Layout:**

- Brutalist grid sensibility. Visible borders, sharp corners (no border-radius). Generous use of whitespace.
- Max content width ~720px for article text.

**Component styles:**

- **Links:** Muted teal (`#5e9e91`), no underline by default, underline on hover. Visited links use a slightly desaturated variant.
- **Code blocks:** Surface background (`#14141f`), monospace text. Syntax highlighting via Pygments using a palette-aligned theme (e.g. `monokai` with adjusted token colours).
- **Tags:** Small bordered pills with muted amber text and border (`#b89c4a`).
- **Callouts:** Surface-coloured boxes with a muted teal left border.
- **Article metadata block:** Clearly separated from body text with a border-top or distinct surface background.
- **Dead wikilinks:** Muted rose (`#7a3b4e`), dashed underline, to indicate a broken link without being distracting.

The design must remain **readable first**. The cyberpunk aesthetic is expressed through colour choices, typography, and structural elements — not through illegibility, excessive animation, or visual noise.

### 6.2 Templating Engine

**Jinja2** with a small template set.

### 6.3 Templates

| Template | Purpose |
|---|---|
| `base.html` | HTML shell: `<head>`, meta tags, nav, footer, CSS link. Defines `{% block content %}`. |
| `_nav.html` | Navigation bar partial: site title link + "All Pages" link. Included by `base.html`. |
| `article.html` | Extends `base.html`. Renders a single article with metadata block (title, date, tags, description) and `body_html | safe`. |
| `home.html` | Extends `base.html`. Renders the home page: ASCII banner, avatar (if configured), then `Home.md` body content. |
| `listing.html` | Extends `base.html`. Renders a list of articles (used for tag pages). |
| `all_pages.html` | Extends `base.html`. Full listing of every published page, grouped by directory path. |

### 6.4 All Pages Listing

The site generates a dedicated **"All Pages"** page at `/all/index.html` that lists **every** published page, including the Home page.

Pages are **grouped by their directory path**, with the path used as a heading. Pages at the root level are grouped under a `/` heading. Within each group, pages are sorted by date descending.

Example rendered output:

```
# All Pages

## /
- Home (15 March 2026)
- About (10 March 2026)

## articles
- My First Post (12 March 2026)
- Another Article (8 March 2026)

## articles/deep
- Nested Post (5 March 2026)
```

This page is linked from the site navigation.

### 6.5 Content Injection: How Rendered HTML Enters Templates

The `templating.py` module is the single point where rendered article HTML meets Jinja2 templates. This contract must be respected by any future template changes to avoid breaking content rendering.

**The flow:**

1. `renderer.py` converts markdown to an HTML string (`article.body_html`). This is a **fragment** — it contains no `<html>`, `<head>`, or `<body>` tags. It is the inner content only (e.g. `<p>`, `<h2>`, `<pre>`, etc.).
2. `templating.py` passes the `Article` object (including `body_html`) to the Jinja2 template as a context variable.
3. The template outputs the HTML fragment using the `| safe` filter to prevent double-escaping.

**Template contract — `article.html`:**

```html
{% extends "base.html" %}

{% block content %}
<article>
  <header class="article-meta">
    <h1>{{ article.title }}</h1>
    <time datetime="{{ article.date.isoformat() }}">{{ article.date.strftime('%d %B %Y') }}</time>
    {% if article.tags %}
    <div class="tags">
      {% for tag in article.tags %}
        <a href="/tags/{{ tag }}/" class="tag">{{ tag }}</a>
      {% endfor %}
    </div>
    {% endif %}
    {% if article.description %}
    <p class="description">{{ article.description }}</p>
    {% endif %}
  </header>

  <div class="article-body">
    {{ article.body_html | safe }}
  </div>
</article>
{% endblock %}
```

**Critical rules for template authors:**

- `article.body_html` **must** always be output with `| safe`. It is pre-rendered HTML from markdown-it-py. Without `| safe`, all tags will be escaped and rendered as visible text.
- The `<div class="article-body">` wrapper is the styling hook. CSS targeting `.article-body h2`, `.article-body p`, `.article-body pre` etc. controls how article content looks. Do not remove this wrapper.
- The metadata block (`<header class="article-meta">`) is separate from the body and should remain above it. Metadata comes from the `Article` object fields, not from `body_html`.
- `base.html` must define a `{% block content %}{% endblock %}` that child templates fill.

**Template contract — `base.html` (minimal structure):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ site.title }}{% endblock %}</title>
  {% if article is defined and article.description %}
  <meta name="description" content="{{ article.description }}">
  {% endif %}
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <nav class="site-nav">
    {% block nav %}{% include "_nav.html" %}{% endblock %}
  </nav>

  <main>
    {% block content %}{% endblock %}
  </main>

  <footer class="site-footer">
    <p>{{ site.title }} — built with <a href="https://github.com/phalt/paulblish">Paulblish</a></p>
  </footer>
</body>
</html>
```

This structure ensures that future template changes (new nav items, footer content, meta tags) can happen without touching the content injection path.

### 6.6 Template Variables

**`article.html`** receives:

```python
{
    "article": Article,          # the full article object
    "site": SiteConfig,          # site-level config (title, base_url, etc.)
}
```

**`listing.html`** receives:

```python
{
    "title": str,                # page title ("All Articles" or "Tagged: python")
    "articles": list[Article],   # sorted by date descending
    "site": SiteConfig,
}
```

**`all_pages.html`** receives:

```python
{
    "groups": dict[str, list[Article]],  # path_prefix -> articles, ordered
    "site": SiteConfig,
}
```

### 6.7 Site Configuration

Site configuration is loaded from one of two sources, tried in order:

1. **`site.toml`** — a TOML file in the root of the source directory (preferred).
2. **`Home.md` frontmatter** — YAML frontmatter fields in the `Home.md` file at the source root (fallback, useful for Obsidian where `.toml` files are inconvenient).

**Method 1: `site.toml`**

```toml
[site]
title = "My Blog"
base_url = "https://username.github.io/blog"
description = "A blog about things."
author = "Paul"
cname = ""                         # optional — custom domain, e.g. "blog.example.com"
avatar = ""                        # optional — path to a square image for the home page
```

**Method 2: `Home.md` frontmatter**

```yaml
---
publish: true
title: "My Blog"
base_url: "https://username.github.io/blog"
description: "A blog about things."
author: "Paul"
cname: ""          # optional
avatar: ""         # optional
---
```

The same required and optional fields apply regardless of source. If `site.toml` is present it takes priority and `Home.md` frontmatter is ignored for configuration purposes.

**Required fields** (in either source): `title`, `base_url`, `description`, `author`.

**Optional fields**: `cname` (default `""`), `avatar` (default `""`).

**CNAME support:** If the `cname` field is set to a non-empty string, the build writes a `CNAME` file to the output root containing that value. This is required for GitHub Pages to serve the site on a custom domain. Example:

```toml
cname = "blog.paulblish.dev"
```

Produces `_site/CNAME` containing `blog.paulblish.dev`. If `cname` is empty or absent, no `CNAME` file is generated.

**Avatar support:** If the `avatar` field is set, it should be a path (relative to the source directory) to a square image. The image is copied to `output/assets/` and rendered on the home page (see §6.9).

If neither `site.toml` nor `Home.md` with the required fields is found, `pb build` exits with an error (exit code 1):

```
Error: No site configuration found in /path/to/source
       Either create a site.toml file or add site config fields to your Home.md frontmatter:

         title, base_url, description, author

       See: https://github.com/phalt/paulblish#site-configuration
```

CLI flags (`--base-url`) override values from whichever source was used.

### 6.8 Navigation Bar

The `base.html` template includes a top-level navigation bar rendered on every page. The nav bar contains a fixed set of links:

| Link | Target | Notes |
|---|---|---|
| Site title | `/` | The site title from `site.toml`, links to the home page |
| All Pages | `/all/` | Links to the all-pages listing |

The nav bar is minimal by design. It is rendered from a partial template (`_nav.html` or inline in `base.html`) so it can be customised by template authors without touching article rendering. The nav bar should visually use the monospace heading font and muted teal accent for the active/hover state.

Future additions (tag index, RSS icon) can be added to the nav bar, but v1 ships with only the two links above.

### 6.9 Home Page Special Content

When `Home.md` is rendered as the site index page, the template includes two additional elements **above** the `Home.md` body content:

**1. ASCII Art Banner**

A pre-formatted ASCII art rendering of the word "Hello" is displayed at the top of the home page inside a `<pre class="ascii-banner">` block. This is hardcoded in the home page template (not in the markdown file). Example:

```
 _   _      _ _
| | | | ___| | | ___
| |_| |/ _ \ | |/ _ \
|  _  |  __/ | | (_) |
|_| |_|\___|_|_|\___/
```

The ASCII art uses the monospace heading font and muted teal colour (`#5e9e91`). It is purely decorative and should be wrapped in an `aria-hidden="true"` attribute for accessibility.

**2. Author Avatar**

If `site.avatar` is configured in `site.toml`, a square image is rendered below the ASCII banner and above the page content:

```html
<div class="home-avatar">
  <img src="/assets/avatar.png" alt="{{ site.author }}" class="avatar" />
</div>
```

The avatar is displayed as a square image (e.g. 120×120px), styled with a 1px border in the muted teal accent colour. No border-radius — sharp corners, consistent with the brutalist aesthetic.

If `site.avatar` is not configured, the avatar section is simply omitted — no placeholder, no broken image.

The home page template structure is:

```
┌─────────────────────────┐
│    ASCII "Hello" art     │
├─────────────────────────┤
│    Avatar (if set)       │
├─────────────────────────┤
│    Home.md body_html     │
└─────────────────────────┘
```

---

## 7. Asset Handling

1. During rendering, collect all image/file references from published articles (`![[file]]` and standard `![](path)` syntax).
2. Resolve each reference against the source directory (Obsidian uses flat or shortest-path matching by default).
3. Copy only referenced assets to `output/assets/`.
4. Rewrite all references in the rendered HTML to point to `/assets/{filename}`.
5. If an asset is referenced but not found, log a warning and render a placeholder/broken-image indicator.

**Collision handling:** if two different directories contain assets with the same filename, disambiguate with a content hash prefix (e.g. `a3f8_photo.png`).

---

## 7.1 RSS/Atom Feed

The build generates an RSS 2.0 feed at `output/feed.xml`, addressable at `/feed.xml` on the deployed site. The feed allows readers to subscribe to new articles via any feed reader.

**Feed metadata (from `site.toml`):**

| Field | Source | Example |
|---|---|---|
| `<title>` | `site.title` | `My Blog` |
| `<link>` | `site.base_url` | `https://example.com` |
| `<description>` | `site.description` | `A blog about things.` |
| `<managingEditor>` | `site.author` | `Paul` |
| `<lastBuildDate>` | Build time | `Tue, 15 Mar 2026 00:00:00 +0000` |

**Feed items:**

Each published article (excluding `Home.md`) becomes an `<item>` in the feed, sorted by date descending (newest first). Maximum 20 items in the feed to keep it lightweight.

| Field | Source |
|---|---|
| `<title>` | `article.title` |
| `<link>` | `site.base_url + article.url_path` |
| `<guid>` | `site.base_url + article.url_path` (permalink) |
| `<pubDate>` | `article.date` in RFC 822 format |
| `<description>` | `article.description` if present, otherwise first 280 characters of `body_markdown` stripped of markup |

**Implementation details:**

- The feed is generated using Python's `xml.etree.ElementTree` (stdlib) — no extra dependency needed.
- The feed URL should be discoverable via a `<link rel="alternate" type="application/rss+xml">` tag in `base.html`'s `<head>`.
- If `site.base_url` is `/` or empty, feed item links use relative paths. Otherwise, full absolute URLs are constructed.

---

## 8. CLI Interface

### 8.1 Tool Name

`pb` — registered as a console script via `pyproject.toml`:

```toml
[project.scripts]
pb = "paulblish.cli:main"
```

### 8.2 Commands

```
pb build --source ~/obsidian/blog --output ./_site
pb build --source ~/obsidian/blog --output ./_site --base-url https://example.com
pb clean --output ./_site
```

### 8.3 `build` Options

| Flag | Default | Description |
|---|---|---|
| `--source`, `-s` | `.` (cwd) | Path to the Obsidian vault directory to scan. Must contain a `site.toml`. |
| `--output`, `-o` | `./_site` | Path to write generated HTML |
| `--base-url` | `/` | Base URL for absolute links and RSS feed (overrides `site.toml`) |
| `--templates` | bundled defaults | Path to custom Jinja2 templates directory |
| `--clean` | `false` | Delete output directory before building |
| `--drafts` | `false` | Include articles with `publish: false` (for local preview) |
| `--verbose`, `-v` | `false` | Verbose logging |

### 8.4 `clean` Options

| Flag | Default | Description |
|---|---|---|
| `--output`, `-o` | `./_site` | Path to delete |

### 8.5 Build Validation

Before scanning any files, `pb build` performs the following checks. Failure at any step exits with code 1.

1. **Source directory exists** — if `--source` does not point to an existing directory, exit with error.
2. **Config source found** — if neither `{source}/site.toml` nor `{source}/Home.md` (case-insensitive) exists, exit with a clear error listing the required fields and linking to documentation.
3. **Config is valid** — if the config source exists but cannot be parsed, or is missing required fields (`title`, `base_url`, `description`, `author`), exit with an error naming the source file and the missing field.

### 8.6 CLI Output

The build command **must** produce clear, structured output showing exactly what it is doing. This is not optional — the output is a core part of the tool's UX.

**Standard output (non-verbose):**

```
Paulblish v0.1.0
Source: ~/obsidian/blog
Config: site.toml ✓

Scanning...

  ✓ articles/my-first-post.md → /articles/my-first-post/
  ✓ articles/deep/bar.md → /articles/deep/bar/
  ✓ Home.md → / (index)
  ✗ articles/draft-idea.md (no publish: true)
  ✗ notes/scratch.md (no frontmatter)
  ✗ random.txt (not markdown)

Building 3 articles, skipped 3 files

  → _site/articles/my-first-post/index.html
  → _site/articles/deep/bar/index.html
  → _site/index.html
  → _site/all/index.html

Done. 3 articles, 1 asset, 0 warnings.
```

**Error output (missing site.toml):**

```
Paulblish v0.1.0
Source: ~/obsidian/blog

Error: No site.toml found in ~/obsidian/blog
       Every source directory must contain a site.toml file.
       See: https://github.com/phalt/paulblish#site-configuration
```

**Key requirements:**

- Every `.md` file found is reported as either picked up (✓) or skipped (✗ with reason).
- Non-markdown files in the directory are listed as skipped if `--verbose` is set; otherwise they are counted but not individually listed.
- The reason for skipping is always shown (no frontmatter, `publish` not true, not a `.md` file).
- Output paths are shown for every file written.
- A summary line reports totals.

**Verbose mode** (`-v`) additionally shows: asset copying, template rendering, wikilink resolution details, and timing information.

### 8.7 Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Build error (missing source dir, missing `site.toml`, invalid config, template error) |
| `2` | Warnings only (dead wikilinks, missing assets) — build still succeeds |

---

## 9. Deployment Workflow

### 9.1 How It Works

The intended workflow is:

1. **Build locally:** Run `pb build --source ~/obsidian/blog --output ./_site` on your own machine. The source directory (your Obsidian vault) lives wherever you keep it — it is **not** part of the Paulblish repository.
2. **Commit the output:** The `_site/` directory is committed to the repository. It contains the fully rendered static site.
3. **Push to deploy:** Pushing to `main` triggers a GitHub Actions workflow that deploys the contents of `_site/` to GitHub Pages. The workflow does **not** install Python, `uv`, or run `pb` — it only deploys pre-built files.

This keeps the CI pipeline trivial and fast (no build step), and means the source Obsidian vault never needs to be committed to the repo.

### 9.2 Repository Layout

```
paulblish/                         # the repo root
├── .github/
│   └── workflows/
│       ├── deploy.yml             # deploys _site/ to GitHub Pages
│       └── test.yml               # runs pytest + ruff on PRs
├── .gitignore                     # .venv/, __pycache__/, etc. — NOT _site/
├── .python-version
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── paulblish/                     # the package (flat layout, like clientele)
│   ├── __init__.py
│   ├── cli.py                     # click entry point
│   ├── config.py                  # SiteConfig loading + site.toml validation
│   ├── models.py                  # Article dataclass, SiteConfig
│   ├── scanner.py                 # directory walk, frontmatter parse, filtering
│   ├── renderer.py                # markdown-it-py setup + plugin chain
│   ├── plugins/                   # markdown-it-py plugins for Obsidian syntax
│   │   ├── __init__.py
│   │   ├── wikilinks.py
│   │   ├── callouts.py
│   │   ├── highlights.py
│   │   └── embeds.py
│   ├── linker.py                  # path lookup table, wikilink resolution
│   ├── assets.py                  # asset discovery, copy, path rewriting
│   ├── templating.py              # Jinja2 environment setup + render
│   └── writer.py                  # output directory creation + file writing
├── templates/                     # default Jinja2 templates, bundled with the package
│   ├── base.html
│   ├── _nav.html
│   ├── article.html
│   ├── home.html
│   ├── listing.html
│   ├── all_pages.html
│   └── static/
│       └── style.css
├── tests/
│   ├── conftest.py
│   ├── test_scanner.py
│   ├── test_renderer.py
│   ├── test_linker.py
│   ├── test_assets.py
│   └── fixtures/                  # sample .md files for testing
│       ├── simple_article.md
│       ├── article_with_wikilinks.md
│       ├── Home.md
│       ├── site.toml              # test fixture config
│       └── assets/
│           └── test_image.png
└── _site/                         # ← generated locally, committed to repo, deployed by CI
    ├── index.html
    ├── all/
    │   └── index.html
    ├── articles/
    │   └── ...
    ├── assets/
    │   └── ...
    └── static/
        └── style.css
```

### 9.3 `.gitignore`

Note: `_site/` is **not** in `.gitignore` — it is committed.

```
.venv/
__pycache__/
*.egg-info/
dist/
```

---

## 10. Dependencies

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "paulblish"
version = "0.1.0"
description = "A cyberpunk static site generator for Obsidian vaults."
readme = "README.md"
license = "MIT"
requires-python = ">=3.13"
authors = [
    { name = "Paul" },
]

dependencies = [
    "python-frontmatter>=1.1",
    "markdown-it-py>=3.0",
    "jinja2>=3.1",
    "pygments>=2.18",
    "click>=8.1",
]

[project.scripts]
pb = "paulblish.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.9",
]

[tool.ruff]
line-length = 120
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## 11. Makefile

Following the clientele convention:

```makefile
.PHONY: install test lint format clean

install:
 uv sync

test:
 uv run pytest

lint:
 uv run ruff check .

format:
 uv run ruff format .

clean:
 rm -rf _site/
 find . -type d -name __pycache__ -exec rm -rf {} +
 find . -type d -name "*.egg-info" -exec rm -rf {} +
```

Note: there is no `make build` target. The `pb build` command requires a `--source` argument pointing to your Obsidian vault, which lives outside this repo. Run it directly:

```
uv run pb build --source ~/obsidian/blog --output ./_site
```

---

## 12. GitHub Actions Workflows

### 12.1 Deploy Workflow

This runs on push to `main` and deploys the pre-built `_site/` directory to GitHub Pages. It does **not** run `pb build` — the site is built locally and committed.

```yaml
name: Deploy Site

on:
  push:
    branches: [main]
    paths:
      - '_site/**'

permissions:
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./_site

      - id: deployment
        uses: actions/deploy-pages@v4
```

This is intentionally minimal. No Python, no `uv`, no build step. Push pre-built HTML → deploy.

### 12.2 Test Workflow

Runs on PRs — linting and tests for the `pb` tool itself.

```yaml
name: Tests

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - run: uv sync

      - run: uv run ruff check .

      - run: uv run pytest
```

---

## 13. Build Pipeline Sequence

```
1. Validate source     (source dir exists?)
2. Validate config     (site.toml exists and is valid?)
3. Load config         (parse site.toml + merge CLI flag overrides)
4. Scan                (walk source dir, parse frontmatter, filter publishable)
5. Report scan         (print ✓/✗ for every file found)
6. Build path map      (note name -> url_path for all published articles)
7. Render              (markdown -> HTML for each article, resolving wikilinks via path map)
8. Collect assets      (find all referenced images/files, including avatar if configured)
9. Copy assets         (to output/assets/, rewrite paths in HTML)
10. Template           (wrap rendered HTML in Jinja2 templates, including metadata block)
11. Generate listings  (all-pages grouped by path, tag pages)
12. Generate CNAME     (write CNAME file if site.cname is configured)
13. Write              (create output directory structure, write all files)
14. Report             (log stats: N articles, N assets, N warnings)
```

---

## 14. README.md

The README must include the following sections:

### 14.1 Required Sections

1. **Header** — Project name, one-line description, badges (Python version, license).
2. **What is this?** — Brief explanation: a CLI tool that converts an Obsidian vault into a static HTML site with a cyberpunk aesthetic. The source vault lives on your machine; the generated output is committed to the repo and deployed via GitHub Pages.
3. **Quick Start** — The full workflow from zero to deployed site:

   ```sh
   git clone https://github.com/phalt/paulblish.git
   cd paulblish
   make install
   uv run pb build --source ~/obsidian/blog --output ./_site
   git add _site/
   git commit -m "Rebuild site"
   git push
   ```

4. **Installation** — How to install for development:

   ```
   git clone https://github.com/phalt/paulblish.git
   cd paulblish
   make install
   ```

5. **Usage** — Full CLI documentation for `pb build` and `pb clean`, with all flags documented.
6. **Site Configuration** — Document the `site.toml` format with all fields (`title`, `base_url`, `description`, `author`, `cname`, `avatar`) and an example. Explain that this file is required and what error you'll see if it's missing. Document custom domain setup via `cname`.
7. **Frontmatter Schema** — Document the full frontmatter contract (`publish`, `title`, `slug`, `date`, `tags`, `description`) with examples.
8. **Directory Structure** — Explain how source directory paths map to output URLs.
9. **The Home File** — Explain the `Home.md` convention, the ASCII banner, and the avatar feature.
10. **Deployment** — Explain the workflow: build locally → commit `_site/` → push → GitHub Actions deploys. Document the GitHub Pages repo settings needed (deploy from Actions). Document custom domain setup via `cname` in `site.toml`.
11. **Development** — How to run tests, lint, format (`make test`, `make lint`, `make format`).
12. **Fork Your Own Copy** (see §14.2).

### 14.2 "Fork Your Own Copy" Section

A dedicated section explaining how someone can copy and run their own instance of Paulblish:

```markdown
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

1. Ensure your markdown files have `publish: true` in their frontmatter.
2. Create a `Home.md` in the root of your content directory for your index page.
3. Build the site:

   ```
   uv run pb build --source /path/to/your/obsidian/dir --output ./_site
   ```

4. Commit the `_site/` directory and push to `main`.
5. In your GitHub repo settings, enable Pages and set it to deploy from GitHub Actions.

The `pb` tool, templates, and styles are all included in the repo.
Customise the templates in `templates/` and the CSS in `templates/static/style.css`
to make it your own.

```

---

## 15. Output Structure

```

_site/
├── CNAME                           # custom domain (only if site.cname is set)
├── index.html                      # Home.md content or article listing fallback
├── all/
│   └── index.html                  # all-pages listing, grouped by path
├── articles/
│   ├── my-first-post/
│   │   └── index.html              # /articles/my-first-post/
│   └── deep/
│       └── bar/
│           └── index.html          # /articles/deep/bar/
├── about/
│   └── index.html                  # /about/ (root-level page)
├── assets/
│   ├── photo.png
│   └── diagram.svg
├── static/
│   └── style.css
├── tags/
│   ├── python/
│   │   └── index.html              # articles tagged "python" (P1)
│   └── tooling/
│       └── index.html
└── feed.xml                        # RSS/Atom feed (P1)

```

---

## 16. Implementation Plan — TODO

The work is ordered so that each step produces a testable, runnable increment.

**Rule: Every implementation step must include test coverage.** Each step either confirms existing tests cover the change and adapts them if needed, or writes new tests before the step is marked as done. Step 1.8 covers any remaining integration-level tests, but unit tests ship with each step.

### Phase 1: Scanner + Renderer (core pipeline)

This is the minimum viable tool — point it at a directory, get HTML files out.

- [x] **1.1** Scaffold the project following clientele conventions: `pyproject.toml` (hatchling backend), flat `paulblish/` package, `Makefile`, `.python-version`, `uv.lock`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `.gitignore` (without `_site/`).
- [x] **1.2** Implement `models.py`: `Article` and `SiteConfig` dataclasses with full type hints. `Article` must include `relative_path`, `path_prefix`, and `url_path` fields for directory-preserving paths.
- [x] **1.3** Implement `config.py`: load and validate `site.toml` from the source directory. Exit with a clear error (code 1) if the file is missing or malformed. CLI flags override individual values.
- [x] **1.4** Implement `scanner.py`: recursive directory walk, frontmatter parsing with `python-frontmatter`, filtering on `publish: true`, title/slug/date resolution logic, `Home.md` detection. Must build `path_prefix` from the file's directory relative to the source root.
- [x] **1.5** Implement `renderer.py`: base `markdown-it-py` setup with Pygments code highlighting. Standard markdown only — no Obsidian plugins yet.
- [x] **1.6** Implement `writer.py`: create output dirs preserving the directory structure (e.g. `_site/articles/foo/index.html`), write rendered HTML with a minimal HTML wrapper (no Jinja2 templates yet).
- [x] **1.7** Implement `cli.py`: wire up `pb build` command with `--source` and `--output` using `click`. Must validate source dir and `site.toml` before scanning. Must print ✓/✗ output for every file scanned, showing picked-up files with their output path and skipped files with the skip reason.
- [x] **1.8** Write tests for: config loading/validation (missing file, invalid TOML, missing `[site]` table), scanner (frontmatter parsing, filtering, slug derivation, path prefix construction, Home detection), and renderer (basic markdown → HTML). Use `tests/fixtures/` with sample `.md` files and a fixture `site.toml`.
- [x] **1.9** Manual test: run against a real Obsidian directory, verify output.

**Milestone:** `uv run pb build -s ~/obsidian/blog -o ./_site` validates `site.toml`, produces HTML files from markdown with directory-preserving paths, and the CLI output clearly shows what was picked up and what was skipped.

### Phase 2: Wikilinks + Linking

- [x] **2.1** Implement `linker.py`: build the path lookup table from scanned articles (note name → `url_path`).
- [x] **2.2** Implement `plugins/wikilinks.py`: `markdown-it-py` plugin to parse `[[wikilink]]` and `[[wikilink|alias]]` syntax, resolve via path map, handle dead links.
- [x] **2.3** Write tests for wikilink resolution (found, not found, aliased, self-referencing, cross-directory links).

**Milestone:** Internal links between published articles work with correct directory-aware paths. Dead links render as styled plain text.

### Phase 3: Templates + Cyberpunk Theme

- [x] **3.1** Create default templates: `base.html` (with `{% block content %}`), `_nav.html` (site title + All Pages link), `article.html`, `home.html`, `listing.html`, `all_pages.html`. Implement the cyberpunk / brutalist theme in `style.css` using the muted CP2077-inspired palette.
- [x] **3.2** Implement the content injection contract in `article.html`: `{{ article.body_html | safe }}` inside `<div class="article-body">`. Document the `| safe` requirement clearly in code comments.
- [x] **3.3** Implement the article metadata block in `article.html`: title as `<h1>`, date, tags (as styled pills linking to tag pages), description as lead paragraph.
- [x] **3.4** Implement `home.html`: ASCII art "Hello" banner (`<pre class="ascii-banner" aria-hidden="true">`), optional avatar image (from `site.avatar`), then `Home.md` body content via `| safe`.
- [x] **3.5** Implement `_nav.html`: site title linking to `/`, "All Pages" linking to `/all/`.
- [x] **3.6** Implement `all_pages.html`: generate the all-pages listing grouped by `path_prefix`, with path headings.
- [x] **3.7** Implement `templating.py`: Jinja2 environment, render article pages (using `article.html`), render home page (using `home.html`), render all-pages page, render tag listing pages.
- [x] **3.8** Update `writer.py` to use templated output. Generate `CNAME` file if `site.cname` is configured.
- [x] **3.9** Add `--templates` and `--base-url` CLI flags.

**Milestone:** Site has the cyberpunk aesthetic, article metadata is visible on every post, the home page shows ASCII art + avatar + content, the nav bar works, the all-pages listing works, and CNAME is generated for custom domains.

### Phase 4: Asset Handling

- [x] **4.1** Implement `assets.py`: scan rendered HTML for image/file references, resolve against source directory.
- [x] **4.2** Implement asset copying with collision-safe naming.
- [x] **4.3** Implement `plugins/embeds.py`: `![[image.png]]` syntax → `<img>` tag with rewritten path.
- [x] **4.4** Write tests for asset discovery, copying, and path rewriting.

**Milestone:** Images and files render correctly in the output.

### Phase 5: Remaining Obsidian Syntax

- [x] **5.1** Implement `plugins/callouts.py`: callout block parsing and HTML rendering.
- [x] **5.2** Implement `plugins/highlights.py`: `==text==` → `<mark>`.
- [x] **5.3** Add footnote support (may be available as an existing `markdown-it-py` plugin).
- [x] **5.4** Add Mermaid support (pass-through to `<pre class="mermaid">` + include mermaid.js in base template).

**Milestone:** Most real-world Obsidian articles render correctly.

### Phase 6: Polish + Deploy

- [x] **6.1** Implement `pb clean` command.
- [x] **6.2** Add `--drafts` flag support.
- [x] **6.3** Generate tag index pages (`/tags/{tag}/index.html`).
- [x] **6.4** Finalise CLI output: build stats, timing, warning summary.
- [x] **6.5** Write both GitHub Actions workflows (`deploy.yml` and `test.yml`).
- [x] **6.6** Write `README.md` with all required sections (see §14), including the "Fork Your Own Copy" guide.
- [x] **6.7** Write `CHANGELOG.md` and `CONTRIBUTING.md`.

**Milestone:** Production-ready. Build locally, commit, push, site deploys automatically. Anyone can fork the repo and have their own blog running in minutes.

### Phase 7: RSS Feed

- [x] **7.1** Implement `feed.py`: generate RSS 2.0 XML from published articles (excluding Home), sorted by date descending, max 20 items. Use `xml.etree.ElementTree` (stdlib). Feed metadata from `SiteConfig`.
- [x] **7.2** Update `writer.py` to call feed generation and write `feed.xml` to the output root.
- [x] **7.3** Update `base.html` to include `<link rel="alternate" type="application/rss+xml">` in `<head>` for feed discovery.
- [x] **7.4** Write tests for: feed XML structure, item count limit, date formatting (RFC 822), Home exclusion, description fallback, feed discovery link in HTML output.

**Milestone:** `/feed.xml` is generated on every build, discoverable via `<link>` tag, and contains the 20 most recent articles with correct metadata.

---

### Phase 8: Extra Features

A collection of high-value improvements and two larger features (light/dark mode toggle and incremental builds) that round out the project from a working tool to a polished, production-quality blog platform.

**Rule: Every implementation step must include test coverage.** Each step either confirms existing tests cover the change and adapts them if needed, or writes new tests before the step is marked done. Documentation must also be updated when each feature is implemented — see the detail sections below.

- [ ] **8.1** Prev / Next article navigation links on every article page.
- [ ] **8.2** Reading time estimate displayed in article header.
- [ ] **8.3** Open Graph and Twitter Card meta tags on every page.
- [ ] **8.4** Generate `sitemap.xml` on every build.
- [ ] **8.5** Generate `robots.txt` on every build.
- [ ] **8.6** Generate a styled `404.html` on every build.
- [ ] **8.7** Light / dark mode toggle with `localStorage` persistence and anti-FOUC inline script.
- [ ] **8.8** Incremental builds via `--incremental` flag and `.pb-manifest.json`.
- [ ] **8.9** Social icons in nav and footer for Bluesky, GitHub, and email.

**Milestone:** All pages include social sharing meta tags, are discoverable by crawlers, have a working 404, support light/dark theming, large vaults can be rebuilt incrementally in a fraction of the full build time, and the site displays the author's social presence via icons in the nav and footer.

---

#### 8.1 — Prev / Next Article Navigation

**What:** Every article page gets navigation links to the chronologically adjacent articles (previous = older, next = newer). The Home article is excluded from the sequence.

**Requirements:**

- Articles are ordered by `date` ascending to form the sequence. Home article is never included.
- The `Article` dataclass gains two optional fields: `prev_article: Article | None = None` and `next_article: Article | None = None`.
- `writer.py` (or a dedicated step in the build pipeline) sets these fields on each article after scanning and sorting, before rendering.
- `article.html` renders a `<nav class="article-nav">` block **below** the `.article-body` div containing:
  - A "← Older" link on the left if `article.prev_article` exists, showing the previous article's title.
  - A "Newer →" link on the right if `article.next_article` exists, showing the next article's title.
  - If only one side exists, the other side renders as an empty placeholder (preserves layout).
- Articles with identical dates retain stable ordering (sort by `url_path` as tiebreaker).
- No new Python dependencies.

**Tests:** prev/next fields set correctly on a sequence of 3+ articles; first article has no `prev`; last article has no `next`; single-article list has neither; Home excluded from sequence; template renders links with correct titles and URLs.

**Documentation:** Update `README.md` — mention prev/next navigation in the "Templates" / article rendering section. Update `CHANGELOG.md`.

---

#### 8.2 — Reading Time Estimate

**What:** Every article displays an estimated reading time ("5 min read") alongside the date in the article header.

**Requirements:**

- The `Article` dataclass gains a `reading_time_minutes: int` field, defaulting to `0`.
- Calculation: count words in `body_markdown` (split on whitespace), divide by 200 (words per minute), round up to nearest whole minute. Minimum value is 1.
- The field is populated in `scanner.py` (or `writer.py` — after rendering) before the article is passed to the template. Since `body_markdown` is available at scan time, populate it in `scanner.py`.
- `article.html` renders the reading time in the `<header class="article-meta">` block, adjacent to the `<time>` element: `<span class="reading-time">{{ article.reading_time_minutes }} min read</span>`.
- Home article also has the field populated but the `home.html` template does not display it (it is not an article in the traditional sense).
- No new Python dependencies.

**Tests:** word count produces correct minute values; minimum 1 minute; round-up behaviour; populated in Article after scan; template renders the span; home template does not render it.

**Documentation:** Update `README.md` frontmatter schema section — note this is auto-calculated. Update `CHANGELOG.md`.

---

#### 8.3 — Open Graph + Twitter Card Meta Tags

**What:** Every page renders a full set of Open Graph and Twitter Card `<meta>` tags so shared links look correct on social media platforms (title, description, image, URL).

**Requirements:**

- Tags are added to `base.html` inside `<head>`, after the existing `<meta name="description">` block.
- The following tags are always rendered (using site-level defaults as fallbacks):

  ```html
  <!-- Open Graph -->
  <meta property="og:type"        content="article">
  <meta property="og:site_name"   content="{{ site.title }}">
  <meta property="og:title"       content="{{ page_title }}">
  <meta property="og:description" content="{{ page_description }}">
  <meta property="og:url"         content="{{ page_url }}">

  <!-- Twitter Card -->
  <meta name="twitter:card"        content="summary">
  <meta name="twitter:title"       content="{{ page_title }}">
  <meta name="twitter:description" content="{{ page_description }}">
  ```

- Template context variables used:
  - `page_title`: `article.title` if an article is in context, otherwise `site.title`.
  - `page_description`: `article.description` if set and non-empty, otherwise `site.description`.
  - `page_url`: `site.base_url + article.url_path` if an article is in context, otherwise `site.base_url`.
- These variables must be passed from every `render_*` function in `templating.py`. All three render functions (`render_article`, `render_all_pages`, `render_tag_page`) must inject them.
- `og:type` is always `"article"` for all pages (this is standard practice for blog content).
- The `og:image` / `twitter:image` tag is **only** rendered if `site.avatar` is configured. When present: `<meta property="og:image" content="{{ site.base_url }}/assets/{{ site.avatar | basename }}">`.
- No new Python dependencies.

**Tests:** OG tags present in article HTML; OG tags use article title/description when available; OG tags fall back to site title/description on listing pages; page URL correct per page type; `og:image` absent when no avatar; `og:image` present and correct when avatar configured.

**Documentation:** Update `README.md` Site Configuration section — document that `avatar` also doubles as the Open Graph image. Update `CHANGELOG.md`.

---

#### 8.4 — `sitemap.xml`

**What:** A standard `sitemap.xml` is generated at `_site/sitemap.xml` on every build, listing all published article URLs. This helps search engine crawlers discover and index all pages.

**Requirements:**

- New function `generate_sitemap(articles, site)` in a new module `paulblish/sitemap.py`. Uses stdlib `xml.etree.ElementTree` (same pattern as `feed.py`).
- Includes all published articles (including Home), tag pages, and the all-pages listing (`/all/`). Does **not** include `robots.txt`, `feed.xml`, `CNAME`, or static assets.
- Each `<url>` entry contains:
  - `<loc>`: the full absolute URL (`site.base_url + url_path`).
  - `<lastmod>`: the article's `date` in `YYYY-MM-DD` format (ISO 8601 date only). For listing pages (`/all/`, `/tags/{tag}/`), use the date of the most recently modified article in that group. If no articles, omit `<lastmod>`.
- XML namespace: `xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"`.
- `writer.py` calls sitemap generation and writes the file, adding the path to the returned written list (so it appears in CLI output).
- `robots.txt` (8.5) will reference this file — coordinate the URL format.

**Tests:** sitemap contains correct `<loc>` for all articles; Home maps to `base_url/`; `<lastmod>` format is YYYY-MM-DD; tag pages and `/all/` included; empty article list produces valid (but empty) sitemap; XML namespace correct; file written to output root.

**Documentation:** Update `README.md` Deployment section — mention sitemap is auto-generated. Update `CHANGELOG.md`.

---

#### 8.5 — `robots.txt`

**What:** A standard `robots.txt` is written to `_site/robots.txt` on every build. It allows all crawlers and points them to `sitemap.xml`.

**Requirements:**

- Content is always the same template, with `site.base_url` interpolated for the `Sitemap:` line:

  ```text
  User-agent: *
  Allow: /

  Sitemap: {site.base_url}/sitemap.xml
  ```

- Written by a new function `write_robots(output_dir, site)` in `writer.py` (no separate module needed — it is trivial).
- Called from `write()` and its path added to the returned written list.
- No new Python dependencies.

**Tests:** file is written; content contains `User-agent: *`; `Sitemap:` line contains the correct absolute URL.

**Documentation:** Update `README.md` Deployment section alongside the sitemap note. Update `CHANGELOG.md`.

---

#### 8.6 — 404 Page

**What:** A styled `_site/404.html` is generated on every build. GitHub Pages automatically serves this file for any URL that doesn't match a file in `_site/`.

**Requirements:**

- New template `templates/404.html` extending `base.html`. Content:
  - An `<h1>` reading "404 — Not Found".
  - A short paragraph: "The page you're looking for doesn't exist."
  - A link back to the site home (`site.base_url`): "← Go home".
  - The page uses the same cyberpunk aesthetic as the rest of the site (inherits from `base.html`).
- New function `render_404(site, templates_dir)` in `templating.py`.
- `writer.py` calls this and writes `output_dir / "404.html"`, adding it to the returned written list.
- No new Python dependencies.

**Tests:** `404.html` is written to the output root; content contains "404"; contains a link to `site.base_url`; valid HTML document.

**Documentation:** Update `README.md` Deployment section — mention GitHub Pages automatically serves `404.html`. Update `CHANGELOG.md`.

---

#### 8.7 — Light / Dark Mode Toggle

**What:** The site gains a persistent light/dark mode toggle button in the nav bar. The default is dark (current cyberpunk theme). The user's preference is remembered across page loads using `localStorage`.

**Requirements:**

- A CSS light theme is defined in `style.css` using a `data-theme="light"` attribute on `<html>`. The light palette should invert the key colours: light background (near-white, e.g. `#f5f5f0`), dark text (e.g. `#1a1a1f`), with the same teal/amber accent colours retained.
- The default theme is dark. `<html>` has no `data-theme` attribute by default (dark styles are the base).
- `_nav.html` renders a toggle button: `<button id="theme-toggle" aria-label="Toggle light/dark mode">◑</button>` (or similar accessible symbol).
- A small inline `<script>` block in `base.html` (before `</body>`) handles:
  1. On page load: read `localStorage.getItem('theme')` and apply `data-theme` to `<html>` if set.
  2. On button click: toggle `data-theme` between `""` (dark) and `"light"`, persist to `localStorage`.
- The script must be minimal vanilla JS — no framework, no external CDN. Keep it under 20 lines.
- The script must run before first paint to avoid flash of wrong theme (FOUC). Place it as an inline `<script>` in `<head>` (not deferred).
- No new Python dependencies.

**Tests:** `_nav.html` contains a theme toggle button; `base.html` contains the anti-FOUC inline script in `<head>`; `style.css` contains `[data-theme="light"]` styles. (Full JS behaviour is not unit-testable in Python — note this explicitly in the test file.)

**Documentation:** Update `README.md` — add a "Theming" section explaining the dark default and light mode toggle. Note that the light theme CSS variables can be customised in `style.css`. Update `CHANGELOG.md`.

---

#### 8.8 — Incremental Builds

**What:** A `--incremental` flag for `pb build` that skips re-rendering articles whose source file has not been modified since the last build. Reduces build time significantly for large vaults.

**Requirements:**

- A build manifest file is written to `output_dir / ".pb-manifest.json"` at the end of every full or incremental build. It contains a JSON object mapping each source file's path (relative to `source_dir`) to its `mtime` (float, seconds since epoch) at the time it was last built:

  ```json
  {
    "articles/foo.md": 1743000000.0,
    "Home.md": 1743000001.5
  }
  ```

- New module `paulblish/manifest.py` with:
  - `load_manifest(output_dir) -> dict[str, float]` — reads `.pb-manifest.json`; returns `{}` if not found or invalid JSON.
  - `save_manifest(output_dir, articles)` — writes the manifest from the current article list's source file mtimes.
- When `--incremental` is passed:
  1. Load the manifest from the output dir.
  2. After scanning, split articles into two groups:
     - **stale**: source file mtime > manifest value (or not in manifest) — must be re-rendered.
     - **fresh**: source file mtime ≤ manifest value — skip rendering and writing; their existing output files are left untouched.
  3. Only stale articles are rendered, templated, and written.
  4. Asset collection and copying still runs over **all** published articles (not just stale ones), so that asset references from fresh articles are not broken.
  5. The all-pages listing, tag pages, RSS feed, sitemap, and robots.txt are always regenerated (they reflect the full article set).
  6. CNAME and 404 are always written (cheap operations).
  7. After the build, save the updated manifest reflecting the current mtimes of **all** published articles.
- CLI output: stale articles print `→ rebuilt`; fresh articles print `(unchanged)` in place of the output path.
- `--incremental` and `--drafts` are compatible: draft articles are included in the manifest when `--drafts` is active.
- No new Python dependencies.

**Tests:** manifest load/save round-trip; fresh articles are not written when `--incremental`; stale articles (mtime changed) are re-rendered; manifest is updated after build; `--incremental` without existing manifest behaves as a full build; listing pages always regenerated; CLI output correctly distinguishes rebuilt vs unchanged.

**Documentation:** Update `README.md` Usage section — document `--incremental` flag under `pb build`. Add a note on when to use it (large vaults). Update `CHANGELOG.md`.

---

#### 8.9 — Social Icons

**What:** If any social contact fields are configured (`bluesky`, `github`, `email`), a row of icon links is rendered in both the site nav bar (right-aligned) and the site footer. Icons are inline SVGs — no external CDN, no JavaScript, no new dependencies.

**Requirements:**

##### Configuration fields

Three new optional fields added to `SiteConfig` (all default to `""`):

- `bluesky` — a Bluesky profile URI, e.g. `"https://bsky.app/profile/paulblish.bsky.social"`. Any non-empty string is treated as the link href.
- `github` — a GitHub profile URI, e.g. `"https://github.com/phalt"`. Any non-empty string is treated as the link href.
- `email` — an email address, e.g. `"paul@example.com"`. Rendered as a `mailto:` link.

These are read from `site.toml` under `[site]` and from `Home.md` frontmatter via the existing `config.py` `get`/fallback mechanism.

##### Template structure

- A new partial template `_social.html` renders the icon row. It is included in both `_nav.html` and `base.html` (footer). Because the same partial appears in two layout positions it must be self-contained — no assumptions about surrounding markup.
- The partial only renders if at least one of the three fields is non-empty. If all three are empty, it renders nothing (no empty `<div>`).
- Output structure:

  ```html
  <div class="social-icons">
    <!-- rendered only if site.github is set -->
    <a href="{{ site.github }}" class="social-icon" aria-label="GitHub" rel="noopener noreferrer" target="_blank">
      <!-- GitHub SVG icon -->
    </a>
    <!-- rendered only if site.bluesky is set -->
    <a href="{{ site.bluesky }}" class="social-icon" aria-label="Bluesky" rel="noopener noreferrer" target="_blank">
      <!-- Bluesky SVG icon -->
    </a>
    <!-- rendered only if site.email is set -->
    <a href="mailto:{{ site.email }}" class="social-icon" aria-label="Email">
      <!-- Envelope SVG icon -->
    </a>
  </div>
  ```

##### Icons

All three icons are inline SVGs with `width="20" height="20" viewBox="0 0 24 24"` and `fill="currentColor"`. This means they inherit their colour from CSS (`color`) and integrate naturally with the theme palette. Using `currentColor` means they match link colour by default and respond to hover states with no extra CSS.

- **GitHub** — the standard GitHub mark (Octocat-free mark): a simplified `<path>` of the GitHub logo silhouette. Use the official path data from the GitHub primer/octicons `mark-github.svg` (24px viewBox).
- **Bluesky** — the Bluesky butterfly logomark SVG path (the AT Protocol / Bluesky official icon).
- **Email** — a minimal envelope icon: a rectangle with a V-shaped flap, readable at 20px.

##### Placement

- `_nav.html`: The social icons `<div>` is placed **after** the existing nav links, pushed to the right end of the nav bar using `margin-left: auto` on the `.social-icons` element (or by adding `flex: 1` spacer — see CSS below).
- `base.html` footer: The `{% include "_social.html" %}` call is added inside `.site-footer`, on a new line below the existing attribution paragraph.

**CSS additions to `style.css`**

```css
/* === Social icons === */
.social-icons {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.site-nav .social-icons {
  margin-left: auto;
}

.social-icon {
  color: var(--text);
  display: flex;
  align-items: center;
  line-height: 1;
}

.social-icon:hover {
  color: var(--accent-teal);
  text-decoration: none;
}

.social-icon svg {
  display: block;
}

.site-footer .social-icons {
  justify-content: center;
  margin-top: 0.5rem;
}
```

**No new Python dependencies.** The SVG path data is hardcoded directly in `_social.html` as inline markup. No Python code changes are required beyond the `SiteConfig` model and `config.py` field additions.

**Tests:**

- `SiteConfig` accepts `bluesky`, `github`, and `email` fields; all default to `""`.
- `config.py` reads each field from `site.toml` and from `Home.md` frontmatter; absent fields default to `""`.
- When all three are empty, `_social.html` renders nothing (empty string / no `.social-icons` div).
- When `site.github` is set, rendered HTML contains the GitHub icon link with correct `href` and `aria-label`.
- When `site.bluesky` is set, rendered HTML contains the Bluesky icon link.
- When `site.email` is set, rendered HTML contains `mailto:` link.
- Social icons appear in the nav HTML (`_nav.html` partial output).
- Social icons appear in the footer HTML (`base.html` output).
- Icon links have `rel="noopener noreferrer"` and `target="_blank"` for external links (GitHub, Bluesky); email link does not have `target="_blank"`.

**Documentation:** Update `README.md` Site Configuration section — add `bluesky`, `github`, `email` to the fields table with descriptions. Update the `site.toml` example block and the `Home.md` frontmatter example to show these fields. Update `CHANGELOG.md`.
