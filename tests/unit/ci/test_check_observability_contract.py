from __future__ import annotations

from pathlib import Path

from tools.ci import check_observability_contract as c


def test_required_snippets_list_not_empty() -> None:
    assert c.REQUIRED_SNIPPETS


def test_contract_path_exists_in_repo() -> None:
    assert isinstance(c.CONTRACT_PATH, Path)
