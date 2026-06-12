"""Unit tests for tools.guardrails.reporters.template."""

from __future__ import annotations

import pytest

from tools.guardrails.reporters.template import ReportTemplate

pytestmark = pytest.mark.unit


@pytest.fixture
def template() -> ReportTemplate:
    return ReportTemplate()


class TestHeader:
    """header() renders markdown headers at the requested level."""

    def test_default_level(self, template: ReportTemplate) -> None:
        assert template.header("Title") == "# Title"

    def test_custom_level(self, template: ReportTemplate) -> None:
        assert template.header("Subtitle", level=3) == "### Subtitle"


class TestSection:
    """section() combines a header and body."""

    def test_renders_header_and_body(self, template: ReportTemplate) -> None:
        result = template.section("Findings", "Nothing to report.")
        assert result == "## Findings\n\nNothing to report."


class TestBulletList:
    """bullet_list() renders each item as a markdown bullet."""

    def test_renders_items(self, template: ReportTemplate) -> None:
        result = template.bullet_list(["one", "two"])
        assert result == "- one\n- two"

    def test_empty_list(self, template: ReportTemplate) -> None:
        assert template.bullet_list([]) == ""


class TestCodeBlock:
    """code_block() wraps code in a fenced block with a language tag."""

    def test_default_language(self, template: ReportTemplate) -> None:
        result = template.code_block("x = 1")
        assert result == "```python\nx = 1\n```"

    def test_custom_language(self, template: ReportTemplate) -> None:
        result = template.code_block("echo hi", lang="bash")
        assert result == "```bash\necho hi\n```"


class TestTable:
    """table() renders a markdown table with header separator."""

    def test_renders_table(self, template: ReportTemplate) -> None:
        result = template.table(["Name", "Score"], [["a.py", "80"], ["b.py", "60"]])
        expected = "| Name | Score |\n| --- | --- |\n| a.py | 80 |\n| b.py | 60 |"
        assert result == expected
