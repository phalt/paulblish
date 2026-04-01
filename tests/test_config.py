from pathlib import Path

import pytest

from paulblish.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadConfig:
    def test_valid_config(self):
        config = load_config(FIXTURES)
        assert config.title == "Test Blog"
        assert config.base_url == "https://example.com"
        assert config.description == "A test blog."
        assert config.author == "Test Author"
        assert config.cname == ""
        assert config.avatar == ""

    def test_missing_file(self, tmp_path):
        with pytest.raises(SystemExit, match="No site.toml found"):
            load_config(tmp_path)

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
        with pytest.raises(SystemExit, match="missing required field"):
            load_config(tmp_path)

    def test_cli_override(self):
        config = load_config(FIXTURES, base_url="https://override.com")
        assert config.base_url == "https://override.com"
        # Other fields unchanged
        assert config.title == "Test Blog"

    def test_none_override_is_ignored(self):
        config = load_config(FIXTURES, base_url=None)
        assert config.base_url == "https://example.com"

    def test_optional_fields_default(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
        )
        config = load_config(tmp_path)
        assert config.cname == ""
        assert config.avatar == ""

    def test_optional_fields_present(self, tmp_path):
        (tmp_path / "site.toml").write_text(
            '[site]\ntitle = "T"\nbase_url = "http://x"\ndescription = "D"\nauthor = "A"\n'
            'cname = "blog.example.com"\navatar = "pic.png"\n'
        )
        config = load_config(tmp_path)
        assert config.cname == "blog.example.com"
        assert config.avatar == "pic.png"
