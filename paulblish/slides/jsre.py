"""Small helpers that reproduce JavaScript string and RegExp behaviour.

The Advanced Slides preprocessor (TypeScript) leans on JavaScript quirks that change its output:

- ``String.prototype.replace`` / ``replaceAll`` expand ``$$``, ``$&``, ``$1`` ... in a *string*
  replacement, even when the pattern is a plain string. A slide containing ``$$`` that is
  "replaced with itself" comes back with ``$``.
- A RegExp with the ``g`` flag keeps ``lastIndex`` between ``test()`` / ``exec()`` calls, so
  re-using one regex across lines can skip matches.
- ``replace`` / ``replaceAll`` with a global regex reset ``lastIndex`` to 0.

Porting the processors faithfully means porting these too, so decks render exactly as they do
in Obsidian.
"""

from __future__ import annotations

import re
from collections.abc import Callable

_FLAGS = {"i": re.I, "m": re.M, "s": re.S}


def compile_js(pattern: str, flags: str = "") -> re.Pattern[str]:
    value = 0
    for flag in flags:
        value |= _FLAGS.get(flag, 0)
    return re.compile(pattern, value)


class JSRegExp:
    """A compiled regex with JavaScript ``lastIndex`` semantics for ``test`` / ``exec``."""

    def __init__(self, pattern: str, flags: str = "") -> None:
        self.source = pattern
        self.flags = flags
        self.is_global = "g" in flags
        self.compiled = compile_js(pattern, flags)
        self.last_index = 0

    def exec(self, string: str) -> re.Match[str] | None:
        if not self.is_global:
            return self.compiled.search(string)
        if self.last_index > len(string):
            self.last_index = 0
            return None
        match = self.compiled.search(string, self.last_index)
        if match is None:
            self.last_index = 0
            return None
        self.last_index = match.end()
        return match

    def test(self, string: str) -> bool:
        return self.exec(string) is not None


def _group(match: re.Match[str], index: int) -> str:
    try:
        value = match.group(index)
    except IndexError:
        return ""
    return value or ""


def expand_replacement(template: str, match: re.Match[str] | None, string: str, start: int, end: int) -> str:
    """Expand a JS replacement template (``$$``, ``$&``, ``$` ``, ``$'``, ``$n``, ``$nn``)."""
    if "$" not in template:
        return template
    group_count = match.re.groups if match is not None else 0
    out: list[str] = []
    i = 0
    length = len(template)
    while i < length:
        char = template[i]
        if char != "$" or i + 1 >= length:
            out.append(char)
            i += 1
            continue
        nxt = template[i + 1]
        if nxt == "$":
            out.append("$")
            i += 2
        elif nxt == "&":
            out.append(string[start:end])
            i += 2
        elif nxt == "`":
            out.append(string[:start])
            i += 2
        elif nxt == "'":
            out.append(string[end:])
            i += 2
        elif nxt.isdigit() and match is not None:
            two = template[i + 1 : i + 3]
            if len(two) == 2 and two.isdigit() and 0 < int(two) <= group_count:
                out.append(_group(match, int(two)))
                i += 3
            elif 0 < int(nxt) <= group_count:
                out.append(_group(match, int(nxt)))
                i += 2
            else:
                out.append("$")
                i += 1
        else:
            out.append("$")
            i += 1
    return "".join(out)


def replace_str(string: str, search: str, replacement: str) -> str:
    """``string.replace(search, replacement)`` with a string pattern: first occurrence only."""
    index = string.find(search)
    if index < 0:
        return string
    end = index + len(search)
    return string[:index] + expand_replacement(replacement, None, string, index, end) + string[end:]


def replace_all_str(string: str, search: str, replacement: str) -> str:
    """``string.replaceAll(search, replacement)`` with a string pattern."""
    if search == "":
        # JS inserts the replacement between every code unit; never needed here
        positions = range(len(string) + 1)
    else:
        positions = []
        index = string.find(search)
        while index >= 0:
            positions.append(index)
            index = string.find(search, index + len(search))
    if not positions:
        return string
    out: list[str] = []
    last = 0
    for index in positions:
        end = index + len(search)
        out.append(string[last:index])
        out.append(expand_replacement(replacement, None, string, index, end))
        last = end
    out.append(string[last:])
    return "".join(out)


Replacement = str | Callable[[re.Match[str]], str]


def replace_re(string: str, regex: JSRegExp | re.Pattern[str], replacement: Replacement, count_all: bool) -> str:
    """``string.replace(regex, replacement)``; *count_all* mirrors the regex's ``g`` flag.

    A callable replacement receives the match and returns the literal text to insert.
    Like JavaScript, a global replace leaves ``lastIndex`` at 0.
    """
    compiled = regex.compiled if isinstance(regex, JSRegExp) else regex
    if isinstance(regex, JSRegExp) and regex.is_global:
        regex.last_index = 0

    def _sub(match: re.Match[str]) -> str:
        if callable(replacement):
            return replacement(match)
        return expand_replacement(replacement, match, string, match.start(), match.end())

    return compiled.sub(_sub, string, count=0 if count_all else 1)


def split_join(string: str, search: str, replacement: str) -> str:
    """``string.split(search).join(replacement)``: a literal replace-all with no ``$`` expansion."""
    if search == "":
        return replacement.join(string)
    return string.replace(search, replacement)
