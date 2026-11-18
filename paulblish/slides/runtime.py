"""Where the deck page loads its runtime from.

Everything Advanced Slides 1.20.0 bundles that is published on npm is loaded from jsDelivr, pinned
to the exact version in the plugin's release bundle (each file was checked byte-for-byte against the
bundle) and guarded with Subresource Integrity. Only the plugin's own build output is vendored in
``templates/reveal/`` (its compiled themes and ``layout.css``), because it isn't published anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

REVEAL_VERSION = "4.3.1"
CHARTJS_VERSION = "3.7.1"
REVEAL_PLUGINS_VERSION = "4.1.5"
FONTAWESOME_VERSION = "5.15.4"
MATHJAX_VERSION = "3.2.0"
HIGHLIGHTJS_VERSION = "11.7.0"

_NPM = "https://cdn.jsdelivr.net/npm"
_REVEAL = f"{_NPM}/reveal.js@{REVEAL_VERSION}"
_PLUGINS = f"{_NPM}/reveal.js-plugins@{REVEAL_PLUGINS_VERSION}"


@dataclass(frozen=True)
class CdnFile:
    url: str
    integrity: str


CDN: dict[str, CdnFile] = {
    "reveal_css": CdnFile(
        f"{_REVEAL}/dist/reveal.css", "sha384-Pb6n6pZwvDREexWRwIahWnEEyJtu7lDuwH2tFEWAsDqluOZa107O/JLlORF2W1Ea"
    ),
    "reveal_js": CdnFile(
        f"{_REVEAL}/dist/reveal.js", "sha384-luD+whv1jI/24ssgrd895PNlDCDdHAs/+LgxvV3PRsv5WHXagPEXwyoQl9PW6+cE"
    ),
    "markdown": CdnFile(
        f"{_REVEAL}/plugin/markdown/markdown.js",
        "sha384-3jCJAHxvHkuDLLXVyAlBmWLk9uFOCQThqCI77I6Bfc1UW1MIzpR8gCkVqqgpRXtZ",
    ),
    "highlight": CdnFile(
        f"{_REVEAL}/plugin/highlight/highlight.js",
        "sha384-AwxnBhLf3YFVM+ub8qUbNxy9nOgbQIm2+ZKfpcyZYgiv20YdB7d0dXaJ4R2kZ8+m",
    ),
    "zoom": CdnFile(
        f"{_REVEAL}/plugin/zoom/zoom.js", "sha384-dNK6r+Pw2VqRj89FBbw8RWb9njeCCF2xbWDBQfut4r1fDpVMy8qmu3OWVvads+Vd"
    ),
    "notes": CdnFile(
        f"{_REVEAL}/plugin/notes/notes.js", "sha384-spW0Hq0iG2d6egl6SJqhiA9SUlXdRTvZo3fQe36GWnw4w1c+Xz5IXjyXpFd1IfVI"
    ),
    "math": CdnFile(
        f"{_REVEAL}/plugin/math/math.js", "sha384-ti1anDVQBFpzxuyrLCUHbO929g/q/AzlUfE/n+fwLn39aZCfcVFOCnjZ3seFTGJs"
    ),
    "chartjs": CdnFile(
        f"{_NPM}/chart.js@{CHARTJS_VERSION}/dist/chart.min.js",
        "sha384-7NrRHqlWUj2hJl3a/dZj/a1GxuQc56mJ3aYsEnydBYrY1jR+RSt6SBvK3sHfj+mJ",
    ),
    "chart": CdnFile(
        f"{_PLUGINS}/chart/plugin.js", "sha384-uPShWZL/xzPg2ZT4kaLmA2xl8aUqq278hUk5BtBMGbfy4e8gx+8dub03NL/t53Om"
    ),
    "customcontrols_js": CdnFile(
        f"{_PLUGINS}/customcontrols/plugin.js",
        "sha384-/BHXMNEnWcV6WbnkM+1vJwk6P95Qpm6NmzSbHW9uOB1LjA7nlFZ8KqWq4N8d8VH+",
    ),
    "customcontrols_css": CdnFile(
        f"{_PLUGINS}/customcontrols/style.css",
        "sha384-CB4kBt8ubXv+S/fFBjzrVgPlucDvQcaaOfm61aBjUsFWv81Rvq5wk0iP1F5U/2Xo",
    ),
    "fontawesome": CdnFile(
        f"{_NPM}/@fortawesome/fontawesome-free@{FONTAWESOME_VERSION}/js/all.min.js",
        "sha384-rOA1PnstxnOBLzCLMcre8ybwbTmemjzdNlILg8O7z1lUkLXozs4DHonlDtnE7fpc",
    ),
}

# Built-in highlight themes, by the name (or plugin-relative path) a deck's `highlightTheme` uses
HIGHLIGHT_THEMES: dict[str, CdnFile] = {
    "monokai": CdnFile(
        f"{_REVEAL}/plugin/highlight/monokai.css",
        "sha384-0rrWATPYzlkqxkUhsXu1QkrO6K3rq4d6FqJQhcCJ7jQcZhb6plkpODMjpoiAYidE",
    ),
    "zenburn": CdnFile(
        f"{_REVEAL}/plugin/highlight/zenburn.css",
        "sha384-sPluGLWICYjbTkVBtJgk093E9FHND5UZpILiTUAXmkMDlguY79gKORAb37jVtirn",
    ),
    "css/vs2015.css": CdnFile(
        f"{_NPM}/highlight.js@{HIGHLIGHTJS_VERSION}/styles/vs2015.css",
        "sha384-BE+nmfgoK1j3fBxbLI64Jzf52Mx/QAyw+4O7GyPYevJnAyrljCoRtQkYNfCfuWPF",
    ),
}
HIGHLIGHT_THEMES["vs2015"] = HIGHLIGHT_THEMES["css/vs2015.css"]

# The math plugin injects this script itself and MathJax then loads its own fonts and extensions
# from the same versioned path, so it can't carry an integrity hash.
MATHJAX_URL = f"{_NPM}/mathjax@{MATHJAX_VERSION}/es5/tex-mml-chtml.js"
