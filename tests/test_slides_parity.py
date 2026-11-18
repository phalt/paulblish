"""Parity with Advanced Slides: every upstream jest snapshot must be reproduced exactly.

tests/fixtures/advanced_slides_snapshots.json is extracted from the plugin's own test
suite (test/*.unit.test.ts + __snapshots__) at v1.20.0: the input markdown, the mocked vault
lookups each test registered, and the snapshot the TypeScript preprocessor produced.
"""

import json
from pathlib import Path

import pytest

from paulblish.slides.preprocessor import Context, load_front, process

FIXTURE = Path(__file__).parent / "fixtures" / "advanced_slides_snapshots.json"
CASES = json.loads(FIXTURE.read_text())

# test/testUtils.ts getSlideOptions defaults
TEST_DEFAULTS = {
    "theme": "black",
    "highlightTheme": "zenburn",
    "template": "template/reveal.html",
    "separator": "\r?\n---\r?\n",
    "verticalSeparator": "\r?\n--\r?\n",
    "enableLinks": False,
    "width": 960,
    "height": 700,
    "margin": 0.04,
}


def _context(case: dict) -> tuple[Context, str]:
    frontmatter, markdown = load_front(case["input"])
    options = {**TEST_DEFAULTS, **frontmatter, **case["extra"]}
    files = case["parse_file"]
    ctx = Context(
        options=options,
        find_file=lambda name: case["find_file"].get(name),
        parse_file=lambda name, header: files.get(name if header is None else f"{name}#{header}"),
        vault_name="test-vault",
    )
    return ctx, markdown


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_upstream_snapshot(case):
    ctx, markdown = _context(case)
    assert process(markdown, ctx) == case["expected"]
