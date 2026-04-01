from datetime import datetime
from pathlib import Path

from paulblish.assets import collect_assets, copy_assets
from paulblish.models import Article


def _make_article(body_markdown: str, slug: str = "test") -> Article:
    return Article(
        source_path=Path(f"/vault/{slug}.md"),
        relative_path=Path(f"{slug}.md"),
        path_prefix="",
        title="Test",
        slug=slug,
        url_path=f"/{slug}/",
        date=datetime(2026, 1, 1),
        body_markdown=body_markdown,
    )


class TestCollectAssets:
    def test_obsidian_embed(self, tmp_path):
        (tmp_path / "photo.png").write_bytes(b"PNG")
        articles = [_make_article("![[photo.png]]")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 1
        assert refs[0].original_ref == "photo.png"
        assert refs[0].source_path == tmp_path / "photo.png"

    def test_markdown_image(self, tmp_path):
        (tmp_path / "img.jpg").write_bytes(b"JPG")
        articles = [_make_article("![alt](img.jpg)")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 1
        assert refs[0].original_ref == "img.jpg"

    def test_external_url_ignored(self, tmp_path):
        articles = [_make_article("![alt](https://example.com/img.png)")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 0

    def test_non_image_ignored(self, tmp_path):
        articles = [_make_article("![[Some Note]]")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 0

    def test_file_not_found(self, tmp_path):
        articles = [_make_article("![[missing.png]]")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 1
        assert refs[0].source_path is None

    def test_flat_resolution(self, tmp_path):
        """Obsidian resolves by filename anywhere in the vault."""
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)
        (subdir / "photo.png").write_bytes(b"PNG")
        articles = [_make_article("![[photo.png]]")]
        refs = collect_assets(articles, tmp_path)
        assert refs[0].source_path == subdir / "photo.png"

    def test_deduplication(self, tmp_path):
        (tmp_path / "photo.png").write_bytes(b"PNG")
        articles = [
            _make_article("![[photo.png]]", slug="a"),
            _make_article("![[photo.png]]", slug="b"),
        ]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 1

    def test_multiple_different_assets(self, tmp_path):
        (tmp_path / "a.png").write_bytes(b"A")
        (tmp_path / "b.jpg").write_bytes(b"B")
        articles = [_make_article("![[a.png]] and ![[b.jpg]]")]
        refs = collect_assets(articles, tmp_path)
        assert len(refs) == 2


class TestCollisionSafeNaming:
    def test_same_filename_different_content(self, tmp_path):
        """Two different files with same basename referenced via explicit paths."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "photo.png").write_bytes(b"content A")
        (dir_b / "photo.png").write_bytes(b"content B")
        articles = [
            _make_article("![](a/photo.png)", slug="post-a"),
            _make_article("![](b/photo.png)", slug="post-b"),
        ]
        refs = collect_assets(articles, tmp_path)
        filenames = {r.output_filename for r in refs}
        # Both should exist with different names
        assert len(filenames) == 2
        # Neither should be plain "photo.png" — both get hash prefixes
        assert "photo.png" not in filenames


class TestCopyAssets:
    def test_copies_to_output(self, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "photo.png").write_bytes(b"PNG data")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        articles = [_make_article("![[photo.png]]")]
        refs = collect_assets(articles, source_dir)
        warnings = copy_assets(refs, output_dir)

        assert len(warnings) == 0
        assert (output_dir / "assets" / "photo.png").exists()
        assert (output_dir / "assets" / "photo.png").read_bytes() == b"PNG data"

    def test_warning_for_missing_file(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        articles = [_make_article("![[missing.png]]")]
        refs = collect_assets(articles, tmp_path)
        warnings = copy_assets(refs, output_dir)

        assert len(warnings) == 1
        assert "missing.png" in warnings[0]

    def test_creates_assets_directory(self, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "img.png").write_bytes(b"IMG")

        output_dir = tmp_path / "output"
        # Don't create output_dir/assets — copy_assets should do it

        articles = [_make_article("![[img.png]]")]
        refs = collect_assets(articles, source_dir)
        copy_assets(refs, output_dir)

        assert (output_dir / "assets" / "img.png").exists()
