from pathlib import Path

import pytest

from paulblish.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadFromToml:
    def test_valid_config(self):
        config, source = load_config(FIXTURES)
        assert config.title == "Test Blog"
        assert config.base_url == "https://example.com"
        assert config.description == "A test blog."
        assert config.author == "Test Author"
        assert config.cname == ""
        assert config.avatar == ""
        assert source == "site.toml"

    def test_invalid_toml(self, tmp_path):
        (tmp_path / "site.toml").write_text("this is [not valid toml{{{")
        with pytest.raises(SystemExit, match="Failed to parse"):
            load_config(tmp_path)

    def test_missing_site_table(self, tmp_path):
        (tmp_path / "site.toml").write_text('[other]\nfoo = "bar"\n')
        with pytest.raises(SystemExit, match="missing the required \\[site\\] table"):
            load_config(tmp_path)

    def test_missing_required_field(self, tmp_path):
        (tmp_path / "site.toml").write_text('[site]\ntitle = "Blog"\n')
        with pytest.raises(SystemExit, match="Missing required config field"):
            load_config(tmp_path)

    def test_cli_override(self):
        config, _ = load_config(FIXTURES, base_url="https://override.com")
        assert config.base_url == "https://override.com"
        assert config.title == "Test Blog"

    def test_none_override_is_ignored(self):
        config, _ = load_config(FIXTURES, base_url=None)
        assert config.base_url == "https://example.com"

    def test_optional_fields_default(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.cname == ""
        assert config.avatar == ""

    def test_optional_fields_present(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
            'cname = "blog.example.com"\navatar = "pic.png"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.cname == "blog.example.com"
        assert config.avatar == "pic.png"


class TestLoadFromHomeFrontmatter:
    def _write_home(self, tmp_path: Path, extra: str = "") -> None:
        content = (
            "---\n"
            "publish: true\n"
            'title: "My Blog"\n'
            'base_url: "https://example.com"\n'
            'description: "A test blog."\n'
            'author: "Test Author"\n'
            f"{extra}"
            "---\n\n# Welcome\n"
        )
        (tmp_path / "Home.md").write_text(content)

    def test_loads_from_home_md_when_no_toml(self, tmp_path):
        self._write_home(tmp_path)
        config, source = load_config(tmp_path)
        assert config.title == "My Blog"
        assert source == "Home.md"
        assert config.base_url == "https://example.com"
        assert config.description == "A test blog."
        assert config.author == "Test Author"

    def test_home_md_case_insensitive(self, tmp_path):
        """home.md (lowercase) is also accepted."""
        content = (
            "---\n"
            "publish: true\n"
            'title: "My Blog"\n'
            'base_url: "https://example.com"\n'
            'description: "A test blog."\n'
            'author: "Test Author"\n'
            "---\n\n# Welcome\n"
        )
        (tmp_path / "home.md").write_text(content)
        config, _ = load_config(tmp_path)
        assert config.title == "My Blog"

    def test_home_md_optional_fields(self, tmp_path):
        self._write_home(tmp_path, 'cname: "myblog.dev"\navatar: "me.png"\n')
        config, _ = load_config(tmp_path)
        assert config.cname == "myblog.dev"
        assert config.avatar == "me.png"

    def test_home_md_optional_fields_default(self, tmp_path):
        self._write_home(tmp_path)
        config, _ = load_config(tmp_path)
        assert config.cname == ""
        assert config.avatar == ""

    def test_home_md_missing_required_field(self, tmp_path):
        (tmp_path / "Home.md").write_text('---\npublish: true\ntitle: "My Blog"\n---\n\n# Welcome\n')
        with pytest.raises(SystemExit, match="Missing required config field"):
            load_config(tmp_path)

    def test_home_md_error_message_names_file(self, tmp_path):
        (tmp_path / "Home.md").write_text('---\npublish: true\ntitle: "My Blog"\n---\n\n# Welcome\n')
        with pytest.raises(SystemExit) as exc_info:
            load_config(tmp_path)
        assert "Home.md" in str(exc_info.value)

    def test_cli_override_with_home_md(self, tmp_path):
        self._write_home(tmp_path)
        config, _ = load_config(tmp_path, base_url="https://override.com")
        assert config.base_url == "https://override.com"
        assert config.title == "My Blog"

    def test_toml_takes_priority_over_home_md(self, tmp_path):
        """site.toml is used even when Home.md also has config fields."""
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "From TOML"\nbase_url = "http://toml"\ndescription = "D"\nauthor = "A"\n'
        )
        self._write_home(tmp_path)  # Home.md has title "My Blog"
        config, _ = load_config(tmp_path)
        assert config.title == "From TOML"


class TestSocialFields:
    def test_social_fields_default_to_empty(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.github == ""
        assert config.bluesky == ""
        assert config.email == ""

    def test_social_fields_loaded_from_toml(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
            'github = "https://github.com/phalt"\n'
            'bluesky = "https://bsky.app/profile/paul.bsky.social"\n'
            'email = "paul@example.com"\n'
        )
        config, _ = load_config(tmp_path)
        assert config.github == "https://github.com/phalt"
        assert config.bluesky == "https://bsky.app/profile/paul.bsky.social"
        assert config.email == "paul@example.com"

    def test_social_fields_loaded_from_home_md(self, tmp_path):
        (tmp_path / "Home.md").write_text(
            "---\n"
            "publish: true\n"
            'title: "T"\nbase_url: "http://x"\ndescription: "D"\nauthor: "A"\n'
            'github: "https://github.com/phalt"\n'
            'email: "paul@example.com"\n'
            "---\n\n# Hi\n"
        )
        config, _ = load_config(tmp_path)
        assert config.github == "https://github.com/phalt"
        assert config.email == "paul@example.com"


class TestNoConfigFound:
    def test_neither_toml_nor_home_exits(self, tmp_path):
        with pytest.raises(SystemExit, match="No site configuration found"):
            load_config(tmp_path)

    def test_error_message_shows_source_dir(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            load_config(tmp_path)
        assert str(tmp_path) in str(exc_info.value)

    def test_error_message_lists_required_fields(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            load_config(tmp_path)
        msg = str(exc_info.value)
        assert "title" in msg
        assert "base_url" in msg
        assert "description" in msg
        assert "author" in msg
