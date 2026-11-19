# Vendored Advanced Slides styles

Slide decks load their runtime from jsDelivr, pinned to the exact versions in the
[Advanced Slides](https://github.com/MSzturc/obsidian-advanced-slides) **1.20.0** release bundle
(`obsidian-advanced-slides.zip`). Every CDN file was checked byte-for-byte against that bundle, and
each `<script>` / `<link>` carries a Subresource Integrity hash. See `paulblish/slides/runtime.py`.

| Library | Version | Loaded from |
| --- | --- | --- |
| reveal.js (core, markdown, highlight, zoom, notes, math, monokai/zenburn themes, Source Sans Pro font) | 4.3.1 | `cdn.jsdelivr.net/npm/reveal.js@4.3.1` |
| reveal.js-plugins (chart, customcontrols) | 4.1.5 | `cdn.jsdelivr.net/npm/reveal.js-plugins@4.1.5` |
| Chart.js | 3.7.1 | `cdn.jsdelivr.net/npm/chart.js@3.7.1` |
| Font Awesome Free | 5.15.4 | `cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@5.15.4` |
| MathJax (loads its own fonts/extensions from the same path) | 3.2.0 | `cdn.jsdelivr.net/npm/mathjax@3.2.0` |
| highlight.js `vs2015` theme | 11.7.0 | `cdn.jsdelivr.net/npm/highlight.js@11.7.0` |
| Pele (mermaid diagrams, shared with article pages) | see `templating.py` | `cdn.jsdelivr.net/npm/pele` |

This directory holds only what is not published anywhere else: the plugin's own build output,
copied from the release bundle. It is copied to `_site/static/reveal/` when a deck is published.

| Path | What | Licence |
| --- | --- | --- |
| `dist/theme/*.css` | The plugin's themes, compiled from its SCSS. They differ from reveal.js's stock themes (selectors, heading weights, chart colours), so the stock CDN themes can't replace them. | MIT (`LICENSE-advanced-slides`) |
| `dist/theme/fonts/league-gothic/league-gothic.css` | Font CSS imported by the league/moon/solarized/beige themes, as bundled (the bundle ships no League Gothic font files either). | SIL OFL 1.1 |
| `css/layout.css` | Grid, split, callout, alignment and animation styles. | MIT (`LICENSE-advanced-slides`) |

Changes from the release bundle:

- `black.css` and `white.css` import Source Sans Pro from the reveal.js 4.3.1 CDN path instead of
  `./fonts/` (the font files are identical).
- Not shipped: the `mattropolis` theme; the chalkboard, menu, search, pointer and elapsed-time-bar
  plugins (their `enable*` frontmatter options are ignored); mermaid.js (Pele draws diagrams).

To upgrade: download a newer release bundle, copy the same paths, update the versions and
integrity hashes in `paulblish/slides/runtime.py` after checking the CDN files match the bundle, and
re-run `tests/test_slides_parity.py` against that version's jest snapshots.
