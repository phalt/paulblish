"""reveal.js markdown slidify port: separators, vertical stacks, speaker notes."""

from paulblish.slides.slidify import slidify

H = "\r?\n---\r?\n"
V = "\r?\n--\r?\n"


def _md(content: str) -> str:
    return f'<script type="text/template">{content}</script>'


def test_horizontal_slides():
    assert slidify("# A\n---\n# B", H, V, "note:") == (
        f"<section  data-markdown>{_md('# A')}</section><section  data-markdown>{_md('# B')}</section>"
    )


def test_vertical_stack():
    html = slidify("# A\n---\n# B\n--\n# C\n---\n# D", H, V, "note:")
    assert html == (
        f"<section  data-markdown>{_md('# A')}</section>"
        f"<section ><section data-markdown>{_md('# B')}</section>"
        f"<section data-markdown>{_md('# C')}</section></section>"
        f"<section  data-markdown>{_md('# D')}</section>"
    )


def test_speaker_notes_become_aside():
    html = slidify("# A\n\nnote: Say **hello**", H, V, "note:")
    assert '<aside class="notes"><p>Say <strong>hello</strong></p>\n</aside>' in html
    assert "note:" not in html


def test_notes_ignored_when_separator_appears_twice():
    # reveal.js only splits notes when the separator occurs exactly once
    html = slidify("note: one\nnote: two", H, V, "note:")
    assert "<aside" not in html


def test_script_end_tags_are_escaped():
    html = slidify("<script>x()</script>", H, V, "note:")
    assert "__SCRIPT_END__" in html
    assert html.count("</script>") == 1


def test_defaults_when_no_separators_given():
    assert slidify("A\n---\nB").count("data-markdown") == 2
