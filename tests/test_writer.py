from datetime import datetime
from pathlib import Path

from paulblish.models import Article, SiteConfig
from paulblish.writer import write, write_cname

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


class TestWriteMultiple:
    def test_writes_all_articles_plus_all_pages(self, tmp_path):
        articles = [
            _make_article("home", is_home=True),
            _make_article("post-one"),
            _make_article("post-two", path_prefix="articles"),
        ]
        written = write(articles, tmp_path, site=SITE)
        # 3 articles + 1 all-pages listing
        assert len(written) == 4
        assert all(p.exists() for p in written)
