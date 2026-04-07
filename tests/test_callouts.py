from datetime import datetime
from pathlib import Path

from paulblish.models import Article
from paulblish.renderer import render


def _make_article(body_markdown: str) -> Article:
    return Article(
        source_path=Path("/vault/test.md"),
        relative_path=Path("test.md"),
        path_prefix="",
        title="Test",
        slug="test",
        url_path="/test/",
        date=datetime(2026, 1, 1),
        body_markdown=body_markdown,
    )


class TestCallouts:
    def test_note_callout(self):
        md = "> [!NOTE]\n> This is a note."
        article = render(_make_article(md))
        assert 'class="callout callout-note"' in article.body_html
        assert 'data-callout="note"' in article.body_html
        assert "This is a note." in article.body_html

    def test_default_title_is_type_label(self):
        """With no custom title, the label defaults to the type name."""
        md = "> [!WARNING]\n> Watch out."
        article = render(_make_article(md))
        assert "Warning" in article.body_html

    def test_custom_title_overrides_type_label(self):
        """`[!tip] Call-outs!` — title must be 'Call-outs!', not 'Tip'."""
        md = "> [!tip] Call-outs!\n> Call-out blocks work too"
        article = render(_make_article(md))
        assert "Call-outs!" in article.body_html
        assert 'class="callout callout-tip"' in article.body_html
        # Type label must NOT appear as the title when a custom title is given
        assert article.body_html.count("Tip") == 0

    def test_custom_title_with_faq_type(self):
        """`[!faq] Foldable call-outs too?` — title must be the custom string, not 'Faq'."""
        md = "> [!faq] Foldable call-outs too?\n> Yes, they work!"
        article = render(_make_article(md))
        assert "Foldable call-outs too?" in article.body_html
        assert 'class="callout callout-faq"' in article.body_html
        assert article.body_html.count("Faq") == 0

    def test_callout_body_wrapper(self):
        md = "> [!TIP]\n> Here is a tip."
        article = render(_make_article(md))
        assert '<div class="callout-body">' in article.body_html
        assert "Here is a tip." in article.body_html

    def test_marker_not_in_body(self):
        md = "> [!NOTE]\n> Body text."
        article = render(_make_article(md))
        assert "[!NOTE]" not in article.body_html

    def test_case_insensitive_type(self):
        md = "> [!note]\n> Lowercase type."
        article = render(_make_article(md))
        assert 'class="callout callout-note"' in article.body_html

    def test_unknown_callout_type(self):
        md = "> [!CUSTOM]\n> Custom callout."
        article = render(_make_article(md))
        assert 'class="callout callout-custom"' in article.body_html
        assert "Custom callout." in article.body_html

    def test_regular_blockquote_unaffected(self):
        md = "> This is just a regular blockquote."
        article = render(_make_article(md))
        assert "<blockquote>" in article.body_html
        assert "callout" not in article.body_html

    def test_danger_callout(self):
        md = "> [!DANGER]\n> Dangerous!"
        article = render(_make_article(md))
        assert 'class="callout callout-danger"' in article.body_html

    def test_callout_closes_with_divs_not_blockquote(self):
        md = "> [!TIP]\n> A tip."
        article = render(_make_article(md))
        assert "</blockquote>" not in article.body_html
        assert article.body_html.count("</div>") >= 2

    def test_multiple_callouts_both_close_correctly(self):
        md = "> [!TIP]\n> First.\n\n> [!NOTE]\n> Second."
        article = render(_make_article(md))
        assert "</blockquote>" not in article.body_html
        assert 'class="callout callout-tip"' in article.body_html
        assert 'class="callout callout-note"' in article.body_html


class TestCollapsibleCallouts:
    def test_plus_modifier_renders_details_open(self):
        md = "> [!TIP]+\n> Expanded by default."
        article = render(_make_article(md))
        assert "<details open>" in article.body_html
        assert "callout-collapsible" in article.body_html
        assert "Expanded by default." in article.body_html

    def test_minus_modifier_renders_details_closed(self):
        md = "> [!NOTE]-\n> Collapsed by default."
        article = render(_make_article(md))
        assert "<details>" in article.body_html
        assert "<details open>" not in article.body_html
        assert "callout-collapsible" in article.body_html
        assert "Collapsed by default." in article.body_html

    def test_collapsible_uses_summary_not_div_for_title(self):
        md = "> [!WARNING]+\n> Watch out."
        article = render(_make_article(md))
        assert '<summary class="callout-title">' in article.body_html
        assert '<div class="callout-title">' not in article.body_html

    def test_collapsible_closes_with_details_tag(self):
        md = "> [!TIP]-\n> A tip."
        article = render(_make_article(md))
        assert "</details>" in article.body_html
        assert "</blockquote>" not in article.body_html

    def test_collapsible_includes_fold_indicator(self):
        md = "> [!NOTE]+\n> Content."
        article = render(_make_article(md))
        assert 'class="callout-fold"' in article.body_html

    def test_no_modifier_is_still_static(self):
        md = "> [!TIP]\n> Static callout."
        article = render(_make_article(md))
        assert "<details" not in article.body_html
        assert "callout-collapsible" not in article.body_html
        assert '<div class="callout-title">' in article.body_html

    def test_collapsible_with_custom_title(self):
        """`[!faq]- Foldable call-outs too?` — title must be the question, not 'Faq'."""
        md = "> [!faq]- Foldable call-outs too?\n> Yes, they work!"
        article = render(_make_article(md))
        assert "Foldable call-outs too?" in article.body_html
        assert "<details>" in article.body_html
        assert article.body_html.count("Faq") == 0

    def test_collapsible_expanded_with_custom_title(self):
        md = "> [!tip]+ My expanded tip\n> Content."
        article = render(_make_article(md))
        assert "My expanded tip" in article.body_html
        assert "<details open>" in article.body_html
        assert article.body_html.count("Tip") == 0

    def test_mixed_static_and_collapsible(self):
        md = "> [!TIP]\n> Static.\n\n> [!NOTE]+\n> Collapsible."
        article = render(_make_article(md))
        assert "callout-collapsible" in article.body_html
        assert '<div class="callout-title">' in article.body_html  # from the static one
        assert "</blockquote>" not in article.body_html
