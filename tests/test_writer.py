from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.writer import assign_prev_next, write, write_404, write_cname, write_robots, write_tag_pages

SITE = SiteConfig(title="Test Blog", base_url="https://example.com", description="Test", author="Tester")


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
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "my-post" / "index.html").exists()

    def test_nested_article(self, tmp_path):
        articles = [_make_article("my-post", path_prefix="articles")]
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "articles" / "my-post" / "index.html").exists()

    def test_deeply_nested_article(self, tmp_path):
        articles = [_make_article("my-post", path_prefix="articles/deep")]
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "articles" / "deep" / "my-post" / "index.html").exists()

    def test_home_article(self, tmp_path):
        articles = [_make_article("home", is_home=True)]
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "index.html").exists()


class TestTemplatedOutput:
    def test_valid_html_document(self, tmp_path):
        articles = [_make_article("post", title="My Title")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

    def test_title_in_head(self, tmp_path):
        articles = [_make_article("post", title="My Title")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "My Title" in content

    def test_article_body_div(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert '<div class="article-body">' in content

    def test_body_html_included(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "<h1>Test</h1>" in content

    def test_meta_charset(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert '<meta charset="utf-8">' in content

    def test_nav_included(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "Test Blog" in content
        assert "/all/" in content

    def test_footer_included(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "Paulblish" in content

    def test_css_link(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "/static/style.css" in content

    def test_article_metadata_block(self, tmp_path):
        article = _make_article("post", title="My Post")
        article.tags = ["python", "testing"]
        article.description = "A description"
        article.date = datetime(2026, 3, 15)
        write([article], tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "article-meta" in content
        assert "My Post" in content
        assert "15 March 2026" in content
        assert "python" in content
        assert "A description" in content


class TestReadingTimeTemplate:
    def test_reading_time_rendered_in_article(self, tmp_path):
        article = _make_article("post")
        article.reading_time_minutes = 5
        write([article], tmp_path, site=SITE)
        content = (tmp_path / "post" / "index.html").read_text()
        assert "5 min read" in content

    def test_home_template_does_not_render_reading_time(self, tmp_path):
        article = _make_article("home", is_home=True)
        article.reading_time_minutes = 3
        write([article], tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert "min read" not in content


class TestHomeOutput:
    def test_home_uses_home_template(self, tmp_path):
        articles = [_make_article("home", is_home=True)]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert "ascii-banner" in content
        assert 'aria-hidden="true"' in content

    def test_home_avatar_when_configured(self, tmp_path):
        site_with_avatar = SiteConfig(
            title="Test", base_url="https://x.com", description="D", author="Paul", avatar="pic.png"
        )
        articles = [_make_article("home", is_home=True)]
        write(articles, tmp_path, site=site_with_avatar)
        content = (tmp_path / "index.html").read_text()
        assert "home-avatar" in content
        assert "pic.png" in content

    def test_home_no_avatar_when_not_configured(self, tmp_path):
        articles = [_make_article("home", is_home=True)]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert "home-avatar" not in content


class TestAllPagesOutput:
    def test_all_pages_written(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "all" / "index.html").exists()

    def test_all_pages_lists_articles(self, tmp_path):
        articles = [_make_article("post", title="My Post")]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "all" / "index.html").read_text()
        assert "All Pages" in content
        assert "My Post" in content

    def test_all_pages_groups_by_prefix(self, tmp_path):
        articles = [
            _make_article("root-post", title="Root Post"),
            _make_article("nested", path_prefix="articles", title="Nested Post"),
        ]
        write(articles, tmp_path, site=SITE)
        content = (tmp_path / "all" / "index.html").read_text()
        assert "/" in content
        assert "articles" in content
        assert "Root Post" in content
        assert "Nested Post" in content


class TestStaticAssets:
    def test_style_css_copied(self, tmp_path):
        articles = [_make_article("post")]
        write(articles, tmp_path, site=SITE)
        assert (tmp_path / "static" / "style.css").exists()


class TestCname:
    def test_cname_written_when_configured(self, tmp_path):
        path = write_cname(tmp_path, "blog.example.com")
        assert path == tmp_path / "CNAME"
        assert path.read_text() == "blog.example.com"

    def test_cname_not_written_when_empty(self, tmp_path):
        path = write_cname(tmp_path, "")
        assert path is None
        assert not (tmp_path / "CNAME").exists()


class TestTagPages:
    def _make_tagged(self, slug: str, tags: list[str]) -> Article:
        a = _make_article(slug)
        a.tags = tags
        return a

    def test_tag_pages_created(self, tmp_path):
        articles = [self._make_tagged("post-a", ["python", "testing"]), self._make_tagged("post-b", ["python"])]
        write_tag_pages(articles, tmp_path, site=SITE)
        assert (tmp_path / "tags" / "python" / "index.html").exists()
        assert (tmp_path / "tags" / "testing" / "index.html").exists()

    def test_tag_page_contains_tagged_articles(self, tmp_path):
        articles = [self._make_tagged("post-a", ["python"]), self._make_tagged("post-b", ["other"])]
        write_tag_pages(articles, tmp_path, site=SITE)
        content = (tmp_path / "tags" / "python" / "index.html").read_text()
        assert "post-a" in content
        assert "post-b" not in content

    def test_tag_page_title(self, tmp_path):
        articles = [self._make_tagged("post-a", ["python"])]
        write_tag_pages(articles, tmp_path, site=SITE)
        content = (tmp_path / "tags" / "python" / "index.html").read_text()
        assert "#python" in content

    def test_no_tags_writes_nothing(self, tmp_path):
        articles = [_make_article("post-a")]
        written = write_tag_pages(articles, tmp_path, site=SITE)
        assert written == []
        assert not (tmp_path / "tags").exists()

    def test_write_includes_tag_pages(self, tmp_path):
        article = _make_article("post-a")
        article.tags = ["python"]
        written = write([article], tmp_path, site=SITE)
        # article + all-pages + tag page
        assert any("tags" in str(p) for p in written)


class TestWrite404:
    def test_404_written(self, tmp_path):
        write_404(tmp_path, SITE)
        assert (tmp_path / "404.html").exists()

    def test_404_contains_heading(self, tmp_path):
        write_404(tmp_path, SITE)
        content = (tmp_path / "404.html").read_text()
        assert "404" in content

    def test_404_contains_home_link(self, tmp_path):
        write_404(tmp_path, SITE)
        content = (tmp_path / "404.html").read_text()
        assert "https://example.com/" in content

    def test_404_is_valid_html(self, tmp_path):
        write_404(tmp_path, SITE)
        content = (tmp_path / "404.html").read_text()
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content

    def test_write_includes_404_in_returned_paths(self, tmp_path):
        articles = [_make_article("post")]
        written = write(articles, tmp_path, site=SITE)
        assert any(p.name == "404.html" for p in written)


class TestWriteRobots:
    def test_robots_txt_written(self, tmp_path):
        write_robots(tmp_path, SITE)
        assert (tmp_path / "robots.txt").exists()

    def test_allows_all_crawlers(self, tmp_path):
        write_robots(tmp_path, SITE)
        content = (tmp_path / "robots.txt").read_text()
        assert "User-agent: *" in content
        assert "Allow: /" in content

    def test_sitemap_url(self, tmp_path):
        write_robots(tmp_path, SITE)
        content = (tmp_path / "robots.txt").read_text()
        assert "Sitemap: https://example.com/sitemap.xml" in content

    def test_write_includes_robots_in_returned_paths(self, tmp_path):
        articles = [_make_article("post")]
        written = write(articles, tmp_path, site=SITE)
        assert any(p.name == "robots.txt" for p in written)


class TestWriteMultiple:
    def test_writes_all_articles_plus_all_pages(self, tmp_path):
        articles = [
            _make_article("home", is_home=True),
            _make_article("post-one"),
            _make_article("post-two", path_prefix="articles"),
        ]
        written = write(articles, tmp_path, site=SITE)
        # 3 articles + 1 all-pages + 0 tag pages + 1 feed.xml + 1 robots.txt + 1 404.html
        assert len(written) == 7
        assert all(p.exists() for p in written)


def _make_dated(slug: str, year: int, title: str = "") -> Article:
    a = _make_article(slug, title=title or slug)
    a.date = datetime(year, 1, 1)
    return a


class TestAssignPrevNext:
    def test_sequence_of_three(self):
        a1 = _make_dated("a", 2020)
        a2 = _make_dated("b", 2021)
        a3 = _make_dated("c", 2022)
        assign_prev_next([a1, a2, a3])
        assert a1.prev_article is None
        assert a1.next_article is a2
        assert a2.prev_article is a1
        assert a2.next_article is a3
        assert a3.prev_article is a2
        assert a3.next_article is None

    def test_first_has_no_prev(self):
        a1 = _make_dated("a", 2020)
        a2 = _make_dated("b", 2021)
        assign_prev_next([a1, a2])
        assert a1.prev_article is None

    def test_last_has_no_next(self):
        a1 = _make_dated("a", 2020)
        a2 = _make_dated("b", 2021)
        assign_prev_next([a1, a2])
        assert a2.next_article is None

    def test_single_article_has_neither(self):
        a = _make_dated("only", 2021)
        assign_prev_next([a])
        assert a.prev_article is None
        assert a.next_article is None

    def test_home_excluded_from_sequence(self):
        home = _make_article("home", is_home=True)
        home.date = datetime(2021, 6, 1)
        a1 = _make_dated("a", 2020)
        a2 = _make_dated("b", 2022)
        assign_prev_next([home, a1, a2])
        assert home.prev_article is None
        assert home.next_article is None
        assert a1.next_article is a2
        assert a2.prev_article is a1

    def test_tiebreaker_by_url_path(self):
        a = _make_article("aaa")
        a.date = datetime(2021, 1, 1)
        b = _make_article("bbb")
        b.date = datetime(2021, 1, 1)
        assign_prev_next([b, a])  # deliberately out of order
        assert a.next_article is b
        assert b.prev_article is a


class TestPrevNextTemplate:
    def test_prev_link_rendered(self, tmp_path):
        older = _make_dated("older", 2020, title="Older Post")
        newer = _make_dated("newer", 2021, title="Newer Post")
        write([older, newer], tmp_path, site=SITE)
        content = (tmp_path / "newer" / "index.html").read_text()
        assert "← Older" in content
        assert "Older Post" in content

    def test_next_link_rendered(self, tmp_path):
        older = _make_dated("older", 2020, title="Older Post")
        newer = _make_dated("newer", 2021, title="Newer Post")
        write([older, newer], tmp_path, site=SITE)
        content = (tmp_path / "older" / "index.html").read_text()
        assert "Newer:" in content
        assert "Newer Post" in content

    def test_no_prev_on_first_article(self, tmp_path):
        a1 = _make_dated("first", 2020)
        a2 = _make_dated("second", 2021)
        write([a1, a2], tmp_path, site=SITE)
        content = (tmp_path / "first" / "index.html").read_text()
        assert "← Older" not in content

    def test_no_next_on_last_article(self, tmp_path):
        a1 = _make_dated("first", 2020)
        a2 = _make_dated("second", 2021)
        write([a1, a2], tmp_path, site=SITE)
        content = (tmp_path / "second" / "index.html").read_text()
        assert "Newer →" not in content

    def test_article_nav_block_present(self, tmp_path):
        a = _make_dated("solo", 2021)
        write([a], tmp_path, site=SITE)
        content = (tmp_path / "solo" / "index.html").read_text()
        assert 'class="article-nav"' in content


class TestHomeLatestArticles:
    def test_latest_articles_shown_on_home(self, tmp_path):
        home = _make_article("home", is_home=True)
        a1 = _make_dated("alpha", 2023, title="Alpha Post")
        a2 = _make_dated("beta", 2022, title="Beta Post")
        a3 = _make_dated("gamma", 2021, title="Gamma Post")
        write([home, a1, a2, a3], tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert "recent-posts" in content
        assert "Alpha Post" in content
        assert "Beta Post" in content
        assert "Gamma Post" in content

    def test_home_shows_at_most_three_latest(self, tmp_path):
        home = _make_article("home", is_home=True)
        articles = [_make_dated(f"post-{i}", 2020 + i, title=f"Post {i}") for i in range(5)]
        write([home] + articles, tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        # Most recent 3 should appear; oldest 2 should not
        assert "Post 4" in content
        assert "Post 3" in content
        assert "Post 2" in content
        assert "Post 1" not in content
        assert "Post 0" not in content

    def test_home_no_recent_posts_without_articles(self, tmp_path):
        home = _make_article("home", is_home=True)
        write([home], tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert "recent-posts" not in content

    def test_home_does_not_show_article_nav(self, tmp_path):
        home = _make_article("home", is_home=True)
        a = _make_dated("post", 2021)
        write([home, a], tmp_path, site=SITE)
        content = (tmp_path / "index.html").read_text()
        assert 'class="article-nav"' not in content
