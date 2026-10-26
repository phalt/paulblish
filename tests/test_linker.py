from datetime import datetime
from pathlib import Path

from paulblish.linker import _normalise, build_path_map
from paulblish.models import Article


def _make_article(title: str, slug: str, url_path: str, path_prefix: str = "", filename: str | None = None) -> Article:
    filename = filename or slug
    return Article(
        source_path=Path(f"/vault/{filename}.md"),
        relative_path=Path(f"{filename}.md"),
        path_prefix=path_prefix,
        title=title,
        slug=slug,
        url_path=url_path,
        date=datetime(2026, 1, 1),
        body_markdown="",
    )


class TestNormalise:
    def test_lowercase(self):
        assert _normalise("Simple Article") == "simple article"

    def test_strip_whitespace(self):
        assert _normalise("  padded  ") == "padded"

    def test_strip_md_extension(self):
        assert _normalise("My Note.md") == "my note"

    def test_strip_md_case_insensitive(self):
        assert _normalise("My Note.MD") == "my note"

    def test_empty_string(self):
        assert _normalise("") == ""


class TestBuildPathMap:
    def test_basic_map(self):
        articles = [
            _make_article("Simple Article", "simple-article", "/simple-article/"),
            _make_article("Another Post", "another-post", "/articles/another-post/", path_prefix="articles"),
        ]
        path_map = build_path_map(articles)
        assert path_map["simple article"] == "/simple-article/"
        assert path_map["another post"] == "/articles/another-post/"

    def test_lookup_is_case_insensitive(self):
        articles = [_make_article("My Title", "my-title", "/my-title/")]
        path_map = build_path_map(articles)
        assert "my title" in path_map

    def test_empty_articles(self):
        assert build_path_map([]) == {}

    def test_cross_directory_articles(self):
        articles = [
            _make_article("Root Post", "root-post", "/root-post/"),
            _make_article("Nested Post", "nested-post", "/articles/deep/nested-post/", path_prefix="articles/deep"),
        ]
        path_map = build_path_map(articles)
        assert path_map["root post"] == "/root-post/"
        assert path_map["nested post"] == "/articles/deep/nested-post/"

    def test_filename_resolves_when_title_differs(self):
        articles = [
            _make_article("Tool widgets", "examples", "/tools/examples/", path_prefix="tools", filename="Tools Widgets")
        ]
        path_map = build_path_map(articles)
        assert path_map["tools widgets"] == "/tools/examples/"
        assert path_map["tool widgets"] == "/tools/examples/"

    def test_filename_wins_over_another_notes_title(self):
        articles = [
            _make_article("Metronome", "practice", "/tools/practice/", filename="Drum practice"),
            _make_article("Metronome tool", "metronome", "/tools/metronome/", filename="Metronome"),
        ]
        path_map = build_path_map(articles)
        assert path_map["metronome"] == "/tools/metronome/"
