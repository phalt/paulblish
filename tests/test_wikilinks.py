from datetime import datetime
from pathlib import Path

from paulblish.models import Article
from paulblish.renderer import render


def _make_article(body_markdown: str, title: str = "Test", slug: str = "test") -> Article:
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title=title,
        slug=slug,
        url_path=f"/{slug}/",
        date=datetime(2026, 1, 1),
        body_markdown=body_markdown,
    )


SAMPLE_PATH_MAP = {
    "simple article": "/simple-article/",
    "another post": "/articles/another-post/",
    "nested post": "/articles/deep/nested-post/",
    "test": "/test/",
}


class TestWikilinkFound:
    def test_basic_wikilink(self):
        article = render(_make_article("Link to [[Simple Article]]"), path_map=SAMPLE_PATH_MAP)
        assert '<a href="/simple-article/">Simple Article</a>' in article.body_html

    def test_wikilink_with_alias(self):
        article = render(_make_article("Link to [[Simple Article|click here]]"), path_map=SAMPLE_PATH_MAP)
        assert '<a href="/simple-article/">click here</a>' in article.body_html

    def test_cross_directory_link(self):
        article = render(_make_article("Link to [[Nested Post]]"), path_map=SAMPLE_PATH_MAP)
        assert '<a href="/articles/deep/nested-post/">Nested Post</a>' in article.body_html

    def test_case_insensitive_lookup(self):
        article = render(_make_article("Link to [[simple article]]"), path_map=SAMPLE_PATH_MAP)
        assert '<a href="/simple-article/">simple article</a>' in article.body_html


class TestWikilinkDead:
    def test_not_found_renders_dead_span(self):
        article = render(_make_article("Link to [[nonexistent note]]"), path_map=SAMPLE_PATH_MAP)
        assert '<span class="wikilink-dead">nonexistent note</span>' in article.body_html

    def test_not_found_with_alias(self):
        article = render(_make_article("Link to [[nonexistent|display]]"), path_map=SAMPLE_PATH_MAP)
        assert '<span class="wikilink-dead">display</span>' in article.body_html

    def test_no_path_map_all_dead(self):
        article = render(_make_article("Link to [[Simple Article]]"))
        assert '<span class="wikilink-dead">Simple Article</span>' in article.body_html


class TestWikilinkSelfReference:
    def test_self_referencing_link(self):
        article = render(_make_article("Link to [[Test]]", title="Test"), path_map=SAMPLE_PATH_MAP)
        assert '<a href="/test/">Test</a>' in article.body_html


class TestWikilinkMultiple:
    def test_multiple_wikilinks_in_one_line(self):
        article = render(
            _make_article("See [[Simple Article]] and [[Another Post]]"),
            path_map=SAMPLE_PATH_MAP,
        )
        assert '<a href="/simple-article/">Simple Article</a>' in article.body_html
        assert '<a href="/articles/another-post/">Another Post</a>' in article.body_html

    def test_mixed_found_and_dead(self):
        article = render(
            _make_article("See [[Simple Article]] and [[missing note]]"),
            path_map=SAMPLE_PATH_MAP,
        )
        assert '<a href="/simple-article/">Simple Article</a>' in article.body_html
        assert '<span class="wikilink-dead">missing note</span>' in article.body_html


class TestWikilinkWithSurroundingMarkdown:
    def test_wikilink_in_paragraph(self):
        md = "This is a **bold** paragraph with [[Simple Article]] in it."
        article = render(_make_article(md), path_map=SAMPLE_PATH_MAP)
        assert "<strong>bold</strong>" in article.body_html
        assert '<a href="/simple-article/">Simple Article</a>' in article.body_html

    def test_wikilink_preserves_other_rendering(self):
        md = "# Heading\n\nSome text with [[Simple Article]] and `code`."
        article = render(_make_article(md), path_map=SAMPLE_PATH_MAP)
        assert "<h1>Heading</h1>" in article.body_html
        assert "<code>code</code>" in article.body_html
        assert '<a href="/simple-article/">Simple Article</a>' in article.body_html
