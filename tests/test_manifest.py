"""Tests for paulblish/manifest.py and the --incremental CLI flag."""

import json
import time
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from paulblish.cli import main
from paulblish.manifest import MANIFEST_FILE, load_manifest, load_manifest_outputs, save_manifest
from paulblish.models import Article, SiteConfig

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SITE = SiteConfig(title="T", base_url="http://x", description="D", author="A")


def _make_article(tmp_path: Path, slug: str, path_prefix: str = "", is_home: bool = False, mtime_offset: float = 0.0) -> Article:
    """Create a real temp source file so stat().st_mtime works."""
    if path_prefix:
        src_dir = tmp_path / path_prefix
        src_dir.mkdir(parents=True, exist_ok=True)
        src = src_dir / f"{slug}.md"
    else:
        tmp_path.mkdir(parents=True, exist_ok=True)
        src = tmp_path / f"{slug}.md"
    src.write_text(f"---\npublish: true\nslug: {slug}\n---\ncontent")

    if mtime_offset:
        new_mtime = src.stat().st_mtime + mtime_offset
        import os
        os.utime(src, (new_mtime, new_mtime))

    url_path = "/" if is_home else (f"/{path_prefix}/{slug}/" if path_prefix else f"/{slug}/")
    return Article(
        source_path=src,
        relative_path=src.relative_to(tmp_path),
        path_prefix=path_prefix,
        title=slug.replace("-", " ").title(),
        slug=slug,
        url_path=url_path,
        date=datetime(2026, 1, 1),
        body_markdown="content",
        body_html="<p>content</p>",
        is_home=is_home,
    )


# ---------------------------------------------------------------------------
# Unit tests for manifest.py
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        assert load_manifest(tmp_path) == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        (tmp_path / MANIFEST_FILE).write_text("not json {{")
        assert load_manifest(tmp_path) == {}

    def test_reads_plain_float_format(self, tmp_path):
        data = {"Home.md": 1743000001.5, "foo.md": 1743000000.0}
        (tmp_path / MANIFEST_FILE).write_text(json.dumps(data))
        result = load_manifest(tmp_path)
        assert result == {"Home.md": 1743000001.5, "foo.md": 1743000000.0}

    def test_reads_rich_format(self, tmp_path):
        data = {
            "Home.md": {"mtime": 1743000001.5, "output": "index.html"},
            "foo.md": {"mtime": 1743000000.0, "output": "foo/index.html"},
        }
        (tmp_path / MANIFEST_FILE).write_text(json.dumps(data))
        result = load_manifest(tmp_path)
        assert result == {"Home.md": 1743000001.5, "foo.md": 1743000000.0}


class TestLoadManifestOutputs:
    def test_returns_output_paths(self, tmp_path):
        data = {
            "Home.md": {"mtime": 1743000001.5, "output": "index.html"},
            "foo.md": {"mtime": 1743000000.0, "output": "foo/index.html"},
        }
        (tmp_path / MANIFEST_FILE).write_text(json.dumps(data))
        result = load_manifest_outputs(tmp_path)
        assert result == {"Home.md": "index.html", "foo.md": "foo/index.html"}

    def test_skips_plain_float_entries(self, tmp_path):
        data = {"foo.md": 1743000000.0}
        (tmp_path / MANIFEST_FILE).write_text(json.dumps(data))
        assert load_manifest_outputs(tmp_path) == {}

    def test_returns_empty_when_missing(self, tmp_path):
        assert load_manifest_outputs(tmp_path) == {}


class TestSaveManifest:
    def test_writes_manifest_file(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = _make_article(source_dir, "my-post")
        save_manifest(output_dir, [article])
        assert (output_dir / MANIFEST_FILE).exists()

    def test_round_trip_mtime(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = _make_article(source_dir, "my-post")
        expected_mtime = article.source_path.stat().st_mtime
        save_manifest(output_dir, [article])
        result = load_manifest(output_dir)
        assert result["my-post.md"] == pytest.approx(expected_mtime)

    def test_saves_output_path(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = _make_article(source_dir, "my-post")
        save_manifest(output_dir, [article])
        outputs = load_manifest_outputs(output_dir)
        assert "my-post.md" in outputs
        assert outputs["my-post.md"] == "my-post/index.html"

    def test_saves_nested_article_output_path(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = _make_article(source_dir, "nested-post", path_prefix="articles")
        save_manifest(output_dir, [article])
        outputs = load_manifest_outputs(output_dir)
        assert outputs["articles/nested-post.md"] == "articles/nested-post/index.html"

    def test_saves_home_article_output_path(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = _make_article(source_dir, "home", is_home=True)
        save_manifest(output_dir, [article])
        outputs = load_manifest_outputs(output_dir)
        assert outputs["home.md"] == "index.html"

    def test_multiple_articles_round_trip(self, tmp_path):
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        a1 = _make_article(source_dir, "post-one")
        a2 = _make_article(source_dir, "post-two")
        save_manifest(output_dir, [a1, a2])
        result = load_manifest(output_dir)
        assert "post-one.md" in result
        assert "post-two.md" in result


# ---------------------------------------------------------------------------
# CLI integration tests for --incremental
# ---------------------------------------------------------------------------


def _make_source(tmp_path: Path) -> Path:
    """Create a minimal vault with site.toml and one published article."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "site.toml").write_text('[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n')
    (source / "article.md").write_text("---\npublish: true\nslug: my-article\n---\nHello")
    return source


class TestIncrementalFlag:
    def test_incremental_without_prior_manifest_behaves_as_full_build(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert result.exit_code == 0
        assert (output / "my-article" / "index.html").exists()

    def test_incremental_writes_manifest(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert (output / MANIFEST_FILE).exists()

    def test_full_build_also_writes_manifest(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        assert (output / MANIFEST_FILE).exists()

    def test_fresh_article_not_rewritten(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        # First build (full)
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        article_html = output / "my-article" / "index.html"
        mtime_after_first = article_html.stat().st_mtime

        # Small sleep to ensure mtime would differ if the file were rewritten
        time.sleep(0.05)

        # Second build (incremental) — article unchanged
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert result.exit_code == 0
        assert article_html.stat().st_mtime == mtime_after_first

    def test_fresh_article_shows_unchanged_in_output(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert "(unchanged)" in result.output

    def test_stale_article_shows_rebuilt_in_output(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        # First build
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])

        # Touch the article to make it stale
        article_src = source / "article.md"
        new_mtime = article_src.stat().st_mtime + 10
        import os
        os.utime(article_src, (new_mtime, new_mtime))

        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert "→ rebuilt" in result.output

    def test_stale_article_is_rewritten(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        # First build
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        article_html = output / "my-article" / "index.html"
        mtime_after_first = article_html.stat().st_mtime

        time.sleep(0.05)

        # Make article stale
        article_src = source / "article.md"
        new_mtime = article_src.stat().st_mtime + 10
        import os
        os.utime(article_src, (new_mtime, new_mtime))

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert article_html.stat().st_mtime > mtime_after_first

    def test_manifest_updated_after_incremental_build(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        manifest_before = load_manifest(output)

        # Touch article to be stale
        article_src = source / "article.md"
        new_mtime = article_src.stat().st_mtime + 10
        import os
        os.utime(article_src, (new_mtime, new_mtime))

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        manifest_after = load_manifest(output)
        assert manifest_after["article.md"] > manifest_before["article.md"]

    def test_listing_page_always_regenerated(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        all_pages = output / "all" / "index.html"
        mtime_first = all_pages.stat().st_mtime

        time.sleep(0.05)

        # Incremental build even with no changes — listings are always written
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert result.exit_code == 0
        assert all_pages.stat().st_mtime > mtime_first

    def test_absent_article_html_deleted(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        # First build — article.md exists and is published
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        article_html = output / "my-article" / "index.html"
        assert article_html.exists()

        # Remove the source file
        (source / "article.md").unlink()

        # Incremental build — absent article's HTML should be deleted
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert result.exit_code == 0
        assert not article_html.exists()

    def test_absent_article_parent_dir_removed(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        article_dir = output / "my-article"
        assert article_dir.exists()

        (source / "article.md").unlink()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert not article_dir.exists()

    def test_absent_article_removed_from_manifest(self, tmp_path):
        source = _make_source(tmp_path)
        output = tmp_path / "_site"
        runner = CliRunner()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])
        assert "article.md" in load_manifest(output)

        (source / "article.md").unlink()

        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])
        assert "article.md" not in load_manifest(output)

    def test_feed_description_preserved_for_fresh_articles_without_frontmatter_description(self, tmp_path):
        """Fresh articles with no frontmatter description must still have non-empty feed descriptions.

        Without the fix, body_html is "" for fresh articles, causing the feed to emit
        empty <description> elements for articles that rely on the body excerpt fallback.
        """
        source = tmp_path / "source"
        source.mkdir()
        (source / "site.toml").write_text('[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n')
        # Deliberately no `description:` field — forces excerpt fallback
        (source / "article.md").write_text(
            "---\npublish: true\nslug: my-article\n---\nThis is the body content of the article."
        )
        output = tmp_path / "_site"
        runner = CliRunner()

        # Full build — excerpt is computed and saved in manifest
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output)])

        # Incremental build — article is unchanged (fresh), body_html never populated
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental"])

        feed = (output / "feed.xml").read_text()
        # The article body text should appear as description, not be empty
        assert "This is the body content" in feed

    def test_incremental_compatible_with_drafts_flag(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "site.toml").write_text('[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n')
        (source / "draft.md").write_text("---\nslug: my-draft\n---\nDraft content")
        output = tmp_path / "_site"
        runner = CliRunner()

        # Full build with --drafts
        runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--drafts"])
        assert "draft.md" in load_manifest(output)

        # Incremental build with both flags
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(output), "--incremental", "--drafts"])
        assert result.exit_code == 0
        assert "(unchanged)" in result.output
