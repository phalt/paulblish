# Vendored presentation runtime

The files in this directory are copied unchanged from the
[Advanced Slides](https://github.com/MSzturc/obsidian-advanced-slides) **1.20.0** release bundle
(`obsidian-advanced-slides.zip`). That is the runtime the Obsidian plugin serves, so decks built by
`pb` look and behave the same as they do in Obsidian. `pb build` copies this directory to
`_site/static/reveal/` when the vault has slide decks.

| Path | Project | Version | Licence |
| --- | --- | --- | --- |
| `dist/reveal.*`, `plugin/{markdown,highlight,zoom,notes,search,math}` | [reveal.js](https://revealjs.com) | 4.3.1 | MIT (`LICENSE-reveal.js`) |
| `dist/theme/*.css`, `css/layout.css`, `css/mattropolis.css` | Advanced Slides (compiled from its SCSS) | 1.20.0 | MIT (`LICENSE-advanced-slides`) |
| `dist/theme/fonts/` | Source Sans Pro, Lato, League Gothic | — | SIL OFL 1.1 |
| `dist/fontawesome/all.min.js` | Font Awesome Free | 5.15.4 | Icons CC BY 4.0, fonts SIL OFL 1.1, code MIT |
| `plugin/math/mathjax/` | MathJax (subset: `tex-mml-chtml.js`, CHTML woff fonts, TeX/MathML extensions, menu, a11y) | 3.2.0 | Apache 2.0 |
| `plugin/highlight/highlight.js` | highlight.js (bundled by reveal.js) | 11 | BSD-3-Clause |
| `plugin/chart/` | reveal.js-plugins chart + Chart.js | Chart.js 3.7.1 | MIT |
| `plugin/chalkboard/`, `plugin/customcontrols/` | reveal.js-plugins | 4.x | MIT |
| `plugin/menu/` | reveal.js-menu | 2.1.0 | MIT (`plugin/menu/LICENSE`) |
| `plugin/reveal-pointer/` | reveal-pointer | — | MIT |
| `plugin/elapsed-time-bar/` | reveal.js-elapsed-time-bar | — | MIT |
| `css/vs2015.css` | highlight.js theme | 11 | BSD-3-Clause |

Changes from the release bundle:

- Removed source maps, `*.esm.js` builds, READMEs and package metadata.
- Removed `plugin/mermaid/` (mermaid.js): diagrams are rendered with [Pele](https://pele.run), like
  the rest of the site.
- MathJax trimmed to the CommonHTML build the plugin loads (`tex-mml-chtml.js`) and the files it
  loads on demand. Speech-rule-engine (`sre/`), the SVG output and the other combined builds are
  not included.

To upgrade, download a newer release bundle, copy the same paths, and re-run the parity tests in
`tests/test_slides_parity.py` against that version's jest snapshots.
