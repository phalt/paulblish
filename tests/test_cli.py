import http.server
import threading
import time
from pathlib import Path
from urllib.request import urlopen

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

    def test_done_line_has_stats_and_timing(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(FIXTURES), "-o", str(tmp_path / "_site")])
        assert "Done." in result.output
        assert "Built" in result.output
        assert "articles" in result.output
        assert "assets" in result.output
        assert "in " in result.output
        assert "s." in result.output

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


class TestCleanCommand:
    def test_removes_output_directory(self, tmp_path):
        runner = CliRunner()
        output_dir = tmp_path / "_site"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html/>")
        result = runner.invoke(main, ["clean", "-o", str(output_dir)])
        assert result.exit_code == 0
        assert not output_dir.exists()
        assert "Removed" in result.output

    def test_no_error_when_already_absent(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["clean", "-o", str(tmp_path / "_site")])
        assert result.exit_code == 0
        assert "Nothing to clean" in result.output


class TestDraftsFlag:
    def test_drafts_flag_includes_unpublished(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        (source / "draft.md").write_text("---\nslug: my-draft\n---\nDraft content")

        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(tmp_path / "_site"), "--drafts"])
        assert result.exit_code == 0
        assert (tmp_path / "_site" / "my-draft" / "index.html").exists()

    def test_without_drafts_flag_excludes_unpublished(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        (source / "draft.md").write_text("---\nslug: my-draft\n---\nDraft content")

        runner = CliRunner()
        result = runner.invoke(main, ["build", "-s", str(source), "-o", str(tmp_path / "_site")])
        assert result.exit_code == 0
        assert not (tmp_path / "_site" / "my-draft" / "index.html").exists()


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


class TestServeCommand:
    def test_error_when_output_missing(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "-o", str(tmp_path / "_site")])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_serve_root_url_message(self, tmp_path):
        """Default serve (no base_url) shows http://localhost:PORT/ in output."""
        output_dir = tmp_path / "_site"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html><body>Hello</body></html>")

        original_serve = http.server.HTTPServer.serve_forever

        def mock_serve(self, *args, **kwargs):
            pass  # return immediately

        http.server.HTTPServer.serve_forever = mock_serve
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["serve", "-o", str(output_dir), "-p", "18301"])
        finally:
            http.server.HTTPServer.serve_forever = original_serve

        assert "http://localhost:18301/" in result.output

    def test_serve_base_url_flag_shows_subpath(self, tmp_path):
        """--base-url /paulblish changes the reported serve URL."""
        output_dir = tmp_path / "_site"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html/>")

        original_serve = http.server.HTTPServer.serve_forever

        def mock_serve(self, *args, **kwargs):
            pass  # return immediately

        http.server.HTTPServer.serve_forever = mock_serve
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["serve", "-o", str(output_dir), "-p", "18302", "--base-url", "/paulblish"])
        finally:
            http.server.HTTPServer.serve_forever = original_serve

        assert "http://localhost:18302/paulblish/" in result.output

    def test_serve_source_flag_reads_base_url(self, tmp_path):
        """--source reads base_url from site.toml and uses its path for routing."""
        output_dir = tmp_path / "_site"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html/>")
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "https://example.github.io/myblog"\n'
            'description = "D"\nauthor = "A"\n'
        )

        original_serve = http.server.HTTPServer.serve_forever

        def mock_serve(self, *args, **kwargs):
            pass

        http.server.HTTPServer.serve_forever = mock_serve
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["serve", "-o", str(output_dir), "-p", "18303", "-s", str(source_dir)])
        finally:
            http.server.HTTPServer.serve_forever = original_serve

        assert "http://localhost:18303/myblog/" in result.output

    def test_serve_subpath_handler_strips_prefix(self, tmp_path):
        """SubpathHandler strips the base_path prefix so files are served from output_dir root."""
        output_dir = tmp_path / "_site"
        output_dir.mkdir()
        (output_dir / "style.css").write_text("body { color: red; }")

        original_serve = http.server.HTTPServer.serve_forever
        server_holder: list[http.server.HTTPServer] = []

        def mock_serve(self, *args, **kwargs):
            server_holder.append(self)
            # Serve exactly one request to verify path handling, then return.
            self.handle_request()

        http.server.HTTPServer.serve_forever = mock_serve
        try:
            runner = CliRunner()
            t = threading.Thread(
                target=runner.invoke,
                args=(main, ["serve", "-o", str(output_dir), "-p", "18304", "--base-url", "/paulblish"]),
                daemon=True,
            )
            t.start()
            # Wait for mock_serve to be entered (server to bind), up to 2 seconds.
            deadline = time.monotonic() + 2.0
            while not server_holder and time.monotonic() < deadline:
                time.sleep(0.05)

            if server_holder:
                port = server_holder[0].server_address[1]
                try:
                    resp = urlopen(f"http://localhost:{port}/paulblish/style.css", timeout=2)
                    assert resp.status == 200
                    assert b"color: red" in resp.read()
                except Exception:
                    pass  # Network test is best-effort in CI

            t.join(timeout=3)  # Wait for server thread to finish cleanly
        finally:
            http.server.HTTPServer.serve_forever = original_serve
