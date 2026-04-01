from datetime import datetime
from pathlib import Path

from paulblish.models import Article
from paulblish.writer import write


def _make_article(slug: str, path_prefix: str = "", is_home: bool = False, title: str = "Test") -> Article:
    if is_home:
        url_path = "/"
    elif path_prefix:
        url_path = f"/{path_prefix}/{slug}/"
    else:
        url_path = f"/{slug}/"

    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix=path_prefix,
        title=title,
        slug=slug,
        url_path=url_path,
        date=datetime(2026, 1, 1),
        body_markdown="# Test",
        body_html="<h1>Test</h1>\n",
        is_home=is_home,
    )


class TestOutputPaths:
    def test_root_level_article(self, tmp_path):
        articles = [_make_article("my-post")]
        written = write(articles, tmp_path)
        assert written == [tmp_path / "my-post" / "index.html"]
        assert written[0].exists()

    def test_nested_article(self, tmp_path):
        articles = [_make_article("my-post", path_prefix="articles")]
        written = write(articles, tmp_path)
        assert written == [tmp_path / "articles" / "my-post" / "index.html"]
        assert written[0].exists()

    def test_deeply_nested_article(self, tmp_path):
        articles = [_make_article("my-post", path_prefix="articles/deep")]
        written = write(articles, tmp_path)
        assert written == [tmp_path / "articles" / "deep" / "my-post" / "index.html"]
        assert written[0].exists()

    def test_home_article(self, tmp_path):
        articles = [_make_article("home", is_home=True)]
        written = write(articles, tmp_path)
        assert written == [tmp_path / "index.html"]
        assert written[0].exists()


class TestHtmlWrapper:
    def test_valid_html_document(self, tmp_path):
        articles = [_make_article("post", title="My Title")]
        write(articles, tmp_path)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

    def test_title_in_head(self, tmp_path):
        articles = [_make_article("post", title="My Title")]
        write(articles, tmp_path)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "<title>My Title</title>" in content

    def test_article_body_div(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path)
        content = (tmp_path / "post" / "index.html").read_text()
        assert '<div class="article-body">' in content

    def test_body_html_included(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "<h1>Test</h1>" in content

    def test_meta_charset(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path)
        content = (tmp_path / "post" / "index.html").read_text()
        assert '<meta charset="utf-8">' in content


class TestWriteMultiple:
    def test_writes_all_articles(self, tmp_path):
        articles = [
            _make_article("home", is_home=True),
            _make_article("post-one"),
            _make_article("post-two", path_prefix="articles"),
        ]
        written = write(articles, tmp_path)
        assert len(written) == 3
        assert all(p.exists() for p in written)

    def test_returns_written_paths(self, tmp_path):
        articles = [_make_article("post")]
        written = write(articles, tmp_path)
        assert len(written) == 1
        assert isinstance(written[0], Path)
