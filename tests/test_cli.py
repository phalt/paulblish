from pathlib import Path

from click.testing import CliRunner

from paulblish.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestBuildCommand:
    def test_successful_build(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site")])
        assert result.exit_code == 0
        assert "Paulblish v0.1.0" in result.output
        assert "Config: site.toml ✓" in result.output
        assert "Done." in result.output

    def test_writes_output_files(self, tmp_path):
        runner = CliRunner()
        output_dir = tmp_path / "_site"
        runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(output_dir)])
        # Home.md -> index.html
        assert (output_dir / "index.html").exists()
        # simple_article.md -> simple-article/index.html
        assert (output_dir / "simple-article" / "index.html").exists()

    def test_shows_picked_up_files(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site")])
        assert "✓" in result.output
        assert "→ / (index)" in result.output  # Home.md

    def test_shows_summary(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site")])
        assert "Building" in result.output
        assert "articles" in result.output

    def test_shows_written_paths(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site")])
        assert "→" in result.output


class TestBuildValidation:
    def test_missing_source_directory(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(tmp_path / "nonexistent"), "-o", str(tmp_path / "_site")])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_missing_site_toml(self, tmp_path):
        runner = CliRunner()
        # tmp_path exists but has no site.toml
        result = runner.invoke(main, ["build", "-s", str(tmp_path), "-o", str(tmp_path / "_site")])
        assert result.exit_code == 1
        assert "site.toml" in result.output


class TestBuildBaseUrlOverride:
    def test_base_url_override(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site"), "--base-url", "https://override.com"],
        )
        assert result.exit_code == 0


class TestBuildSkippedFiles:
    def test_skipped_files_shown(self, tmp_path):
        # Create a source dir with a file missing slug
        source = tmp_path / "source"
        source.mkdir()
        (source / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        (source / "draft.md").write_text("---\npublish: false\nslug: draft\n---\nDraft content")
        (source / "good.md").write_text("---\npublish: true\nslug: good\n---\nGood content")

        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(tmp_path / "_site")])
        assert result.exit_code == 0
        assert "✗" in result.output
        assert "✓" in result.output
        assert "Building 1 articles, skipped 1 files" in result.output
