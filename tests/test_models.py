from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig


class TestArticle:
    def test_required_fields(self):
        article = Article(
            source_path=Path("/vault/foo.md"),
            relative_path=Path("foo.md"),
            path_prefix="",
            title="Foo",
            slug="foo",
            url_path="/foo/",
            date=datetime(2026, 3, 15),
            body_markdown="# Foo\n\nHello.",
        )
        assert article.source_path == Path("/vault/foo.md")
        assert article.relative_path == Path("foo.md")
        assert article.path_prefix == ""
        assert article.title == "Foo"
        assert article.slug == "foo"
        assert article.url_path == "/foo/"
        assert article.date == datetime(2026, 3, 15)
        assert article.body_markdown == "# Foo\n\nHello."

    def test_defaults(self):
        article = Article(
            source_path=Path("/vault/foo.md"),
            relative_path=Path("foo.md"),
            path_prefix="",
            title="Foo",
            slug="foo",
            url_path="/foo/",
            date=datetime(2026, 3, 15),
            body_markdown="# Foo",
        )
        assert article.tags == []
        assert article.description == ""
        assert article.body_html == ""
        assert article.is_home is False
        assert article.assets == []

    def test_defaults_are_independent_instances(self):
        a = Article(
            source_path=Path("/vault/a.md"),
            relative_path=Path("a.md"),
            path_prefix="",
            title="A",
            slug="a",
            url_path="/a/",
            date=datetime(2026, 1, 1),
            body_markdown="",
        )
        b = Article(
            source_path=Path("/vault/b.md"),
            relative_path=Path("b.md"),
            path_prefix="",
            title="B",
            slug="b",
            url_path="/b/",
            date=datetime(2026, 1, 1),
            body_markdown="",
        )
        a.tags.append("python")
        a.assets.append(Path("img.png"))
        assert b.tags == []
        assert b.assets == []

    def test_with_path_prefix(self):
        article = Article(
            source_path=Path("/vault/articles/deep/bar.md"),
            relative_path=Path("articles/deep/bar.md"),
            path_prefix="articles/deep",
            title="Bar",
            slug="bar",
            url_path="/articles/deep/bar/",
            date=datetime(2026, 3, 15),
            body_markdown="# Bar",
        )
        assert article.path_prefix == "articles/deep"
        assert article.url_path == "/articles/deep/bar/"


class TestSiteConfig:
    def test_required_fields(self):
        config = SiteConfig(
            title="My Blog",
            base_url="https://example.com",
            description="A blog.",
            author="Paul",
        )
        assert config.title == "My Blog"
        assert config.base_url == "https://example.com"
        assert config.description == "A blog."
        assert config.author == "Paul"

    def test_defaults(self):
        config = SiteConfig(
            title="My Blog",
            base_url="https://example.com",
            description="A blog.",
            author="Paul",
        )
        assert config.cname == ""
        assert config.avatar == ""

    def test_optional_fields(self):
        config = SiteConfig(
            title="My Blog",
            base_url="https://example.com",
            description="A blog.",
            author="Paul",
            cname="blog.example.com",
            avatar="avatar.png",
        )
        assert config.cname == "blog.example.com"
        assert config.avatar == "avatar.png"
