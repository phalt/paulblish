from datetime import datetime
from pathlib import Path

from paulblish.scanner import scan

FIXTURES = Path(__file__).parent / "fixtures"


def _write_md(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestReadingTime:
    def test_basic_calculation(self, tmp_path):
        # 200 words → exactly 1 minute
        words = " ".join(["word"] * 200)
        (tmp_path / "post.md").write_text(f"---\npublish: true\nslug: post\n---\n{words}")
        articles, _ = scan(tmp_path)
        assert articles[0].reading_time_minutes == 1

    def test_rounds_up(self, tmp_path):
        # 201 words → 2 minutes (ceil)
        words = " ".join(["word"] * 201)
        (tmp_path / "post.md").write_text(f"---\npublish: true\nslug: post\n---\n{words}")
        articles, _ = scan(tmp_path)
        assert articles[0].reading_time_minutes == 2

    def test_minimum_one_minute(self, tmp_path):
        (tmp_path / "post.md").write_text("---\npublish: true\nslug: post\n---\nHello.")
        articles, _ = scan(tmp_path)
        assert articles[0].reading_time_minutes == 1

    def test_empty_body_still_one_minute(self, tmp_path):
        (tmp_path / "post.md").write_text("---\npublish: true\nslug: post\n---\n")
        articles, _ = scan(tmp_path)
        assert articles[0].reading_time_minutes == 1

    def test_home_article_also_gets_reading_time(self, tmp_path):
        words = " ".join(["word"] * 400)
        (tmp_path / "Home.md").write_text(f"---\npublish: true\nslug: home\n---\n{words}")
        articles, _ = scan(tmp_path)
        assert articles[0].reading_time_minutes == 2


class TestDraftsFlag:
    def test_drafts_includes_unpublished(self, tmp_path):
        (tmp_path / "draft.md").write_text("---\nslug: my-draft\n---\nDraft content")
        (tmp_path / "published.md").write_text("---\npublish: true\nslug: pub\n---\nPublished")
        articles, skipped = scan(tmp_path, include_drafts=True)
        slugs = {a.slug for a in articles}
        assert "my-draft" in slugs
        assert "pub" in slugs
        assert not any(s.reason == "publish is not true" for s in skipped)

    def test_without_drafts_excludes_unpublished(self, tmp_path):
        (tmp_path / "draft.md").write_text("---\nslug: my-draft\n---\nDraft content")
        articles, skipped = scan(tmp_path, include_drafts=False)
        assert not articles
        assert any(s.reason == "publish is not true" for s in skipped)

    def test_drafts_still_requires_slug(self, tmp_path):
        (tmp_path / "noslug.md").write_text("---\ntitle: No Slug\n---\nContent")
        articles, skipped = scan(tmp_path, include_drafts=True)
        assert not articles
        assert any("slug" in s.reason for s in skipped)


class TestNullTagsHandling:
    def test_explicit_null_tags_becomes_empty_list(self, tmp_path):
        (tmp_path / "post.md").write_text("---\npublish: true\nslug: post\ntags: null\n---\nContent")
        articles, _ = scan(tmp_path)
        assert articles[0].tags == []

    def test_missing_tags_becomes_empty_list(self, tmp_path):
        (tmp_path / "post.md").write_text("---\npublish: true\nslug: post\n---\nContent")
        articles, _ = scan(tmp_path)
        assert articles[0].tags == []


class TestScanFixtures:
    """Test scanning the existing fixtures directory."""

    def test_scan_fixtures_picks_up_published_articles(self):
        articles, skipped = scan(FIXTURES)
        slugs = {a.slug for a in articles}
        assert "simple-article" in slugs
        assert "article-with-wikilinks" in slugs
        assert "permalink-test" in slugs
        assert "home" in slugs

    def test_scan_fixtures_permalink_article(self):
        articles, _ = scan(FIXTURES)
        permalink_article = [a for a in articles if a.slug == "permalink-test"][0]
        assert permalink_article.title == "Permalink Article"
        assert permalink_article.url_path == "/permalink-test/"
        assert permalink_article.description == "An article using permalink instead of slug."

    def test_scan_fixtures_home_detection(self):
        articles, _ = scan(FIXTURES)
        home = [a for a in articles if a.is_home]
        assert len(home) == 1
        assert home[0].url_path == "/"
        assert home[0].slug == "home"

    def test_scan_fixtures_article_fields(self):
        articles, _ = scan(FIXTURES)
        simple = [a for a in articles if a.slug == "simple-article"][0]
        assert simple.title == "Simple Article"
        assert simple.date == datetime(2026, 3, 15)
        assert simple.tags == ["python", "testing"]
        assert simple.description == "A simple test article."
        assert simple.url_path == "/simple-article/"
        assert simple.path_prefix == ""
        assert simple.is_home is False
        assert "**bold**" in simple.body_markdown


class TestSlugResolution:
    def test_slug_from_frontmatter(self, tmp_path):
        _write_md(tmp_path / "site.toml", "")  # not needed by scanner but keeping dir clean
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: my-post\n---\nHello")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 1
        assert articles[0].slug == "my-post"

    def test_permalink_as_slug_alias(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\npermalink: my-link\n---\nHello")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 1
        assert articles[0].slug == "my-link"

    def test_slug_takes_precedence_over_permalink(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: the-slug\npermalink: the-permalink\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].slug == "the-slug"

    def test_slug_with_leading_slash_is_stripped(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: /articles/my-post\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].slug == "articles/my-post"
        assert "//" not in articles[0].url_path

    def test_slug_with_trailing_slash_is_stripped(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: my-post/\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].slug == "my-post"

    def test_missing_slug_and_permalink_skips(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\ntitle: No Slug\n---\nHello")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 0
        assert len(skipped) == 1
        assert "missing slug" in skipped[0].reason


class TestTitleResolution:
    def test_title_from_frontmatter(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: p\ntitle: FM Title\n---\n# Body H1")
        articles, _ = scan(tmp_path)
        assert articles[0].title == "FM Title"

    def test_title_from_h1(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: p\n---\n# My Heading\n\nBody text")
        articles, _ = scan(tmp_path)
        assert articles[0].title == "My Heading"

    def test_title_from_filename(self, tmp_path):
        _write_md(tmp_path / "my-cool-post.md", "---\npublish: true\nslug: p\n---\nNo heading here")
        articles, _ = scan(tmp_path)
        assert articles[0].title == "My Cool Post"


class TestDateResolution:
    def test_date_from_frontmatter(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: p\ndate: 2026-03-15\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].date == datetime(2026, 3, 15)

    def test_date_from_mtime(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: p\n---\nHello")
        articles, _ = scan(tmp_path)
        assert isinstance(articles[0].date, datetime)


class TestPublishFiltering:
    def test_publish_false_skipped(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: false\nslug: p\n---\nHello")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 0
        assert "publish is not true" in skipped[0].reason

    def test_publish_string_false_skipped(self, tmp_path):
        """publish: \"false\" (quoted string) must NOT be treated as published."""
        _write_md(tmp_path / "post.md", '---\npublish: "false"\nslug: p\n---\nHello')
        articles, skipped = scan(tmp_path)
        assert len(articles) == 0
        assert "publish is not true" in skipped[0].reason

    def test_publish_string_true_included(self, tmp_path):
        """publish: \"true\" (quoted string) should still be treated as published."""
        _write_md(tmp_path / "post.md", '---\npublish: "true"\nslug: p\n---\nHello')
        articles, _ = scan(tmp_path)
        assert len(articles) == 1

    def test_no_frontmatter_skipped(self, tmp_path):
        _write_md(tmp_path / "post.md", "Just plain markdown, no frontmatter")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 0
        assert "publish is not true" in skipped[0].reason

    def test_missing_publish_key_skipped(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\ntitle: Draft\nslug: p\n---\nHello")
        articles, skipped = scan(tmp_path)
        assert len(articles) == 0


class TestPathPrefix:
    def test_root_file_has_empty_prefix(self, tmp_path):
        _write_md(tmp_path / "post.md", "---\npublish: true\nslug: post\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].path_prefix == ""
        assert articles[0].url_path == "/post/"

    def test_nested_file_preserves_directory(self, tmp_path):
        _write_md(tmp_path / "articles" / "post.md", "---\npublish: true\nslug: post\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].path_prefix == "articles"
        assert articles[0].url_path == "/articles/post/"

    def test_deeply_nested_file(self, tmp_path):
        _write_md(tmp_path / "articles" / "deep" / "post.md", "---\npublish: true\nslug: post\n---\nHello")
        articles, _ = scan(tmp_path)
        assert articles[0].path_prefix == "articles/deep"
        assert articles[0].url_path == "/articles/deep/post/"


class TestHomeDetection:
    def test_home_at_root(self, tmp_path):
        _write_md(tmp_path / "Home.md", "---\npublish: true\nslug: home\n---\nWelcome")
        articles, _ = scan(tmp_path)
        assert articles[0].is_home is True
        assert articles[0].url_path == "/"

    def test_home_case_insensitive(self, tmp_path):
        _write_md(tmp_path / "home.md", "---\npublish: true\nslug: home\n---\nWelcome")
        articles, _ = scan(tmp_path)
        assert articles[0].is_home is True

    def test_home_in_subdirectory_is_not_home(self, tmp_path):
        _write_md(tmp_path / "articles" / "Home.md", "---\npublish: true\nslug: home\n---\nNot home")
        articles, _ = scan(tmp_path)
        assert articles[0].is_home is False
        assert articles[0].url_path == "/articles/home/"
