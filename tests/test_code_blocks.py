"""Tests for enhanced code block rendering — wrapper, header, copy button, filename, line numbers."""

from datetime import datetime
from pathlib import Path

from paulblish.models import Article
from paulblish.renderer import render


def _make_article(body_markdown: str) -> Article:
    return Article(
        source_path=Path("/vault/test.md"),
        relative_path=Path("test.md"),
        path_prefix="",
        title="Test",
        slug="test",
        url_path="/test/",
        date=datetime(2026, 1, 1),
        body_markdown=body_markdown,
    )


class TestCodeBlockWrapper:
    def test_known_language_wrapped_in_code_block(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert 'class="code-block"' in article.body_html

    def test_code_block_has_data_lang(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert 'data-lang="python"' in article.body_html

    def test_no_wrapper_for_unknown_language(self):
        article = render(_make_article("```notreallylang\ncode\n```"))
        assert 'class="code-block"' not in article.body_html

    def test_no_wrapper_for_plain_block(self):
        article = render(_make_article("```\ncode\n```"))
        assert 'class="code-block"' not in article.body_html

    def test_mermaid_not_wrapped(self):
        article = render(_make_article("```mermaid\ngraph TD\n  A --> B\n```"))
        assert 'class="code-block"' not in article.body_html


class TestCodeHeader:
    def test_header_present(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert 'class="code-header"' in article.body_html

    def test_header_shows_language(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert 'class="code-lang">python<' in article.body_html

    def test_copy_button_present(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert 'class="code-copy-btn"' in article.body_html


class TestFilename:
    def test_title_attr_shown_instead_of_lang(self):
        article = render(_make_article('```python title="app.py"\nx = 1\n```'))
        assert 'class="code-lang">app.py<' in article.body_html

    def test_title_single_quotes(self):
        article = render(_make_article("```python title='main.py'\nx = 1\n```"))
        assert 'class="code-lang">main.py<' in article.body_html

    def test_no_title_falls_back_to_lang(self):
        article = render(_make_article("```javascript\nconst x = 1;\n```"))
        assert 'class="code-lang">javascript<' in article.body_html


class TestLineNumbers:
    def test_linenos_flag_adds_table(self):
        article = render(_make_article("```python linenos\nx = 1\n```"))
        assert "highlighttable" in article.body_html

    def test_no_linenos_flag_no_table(self):
        article = render(_make_article("```python\nx = 1\n```"))
        assert "highlighttable" not in article.body_html

    def test_linenos_with_title(self):
        article = render(_make_article('```python linenos title="app.py"\nx = 1\n```'))
        assert "highlighttable" in article.body_html
        assert 'class="code-lang">app.py<' in article.body_html
