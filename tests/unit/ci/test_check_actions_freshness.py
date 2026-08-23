"""Unit tests for tools/ci/check_actions_freshness.py."""

from __future__ import annotations

from pathlib import Path

from tools.ci import check_actions_freshness as freshness


def test_parse_version_handles_v_prefix() -> None:
    assert freshness._parse_version("v7.0.1") == (7, 0, 1)


def test_parse_version_rejects_non_semver() -> None:
    assert freshness._parse_version("latest") is None


def test_scan_pinned_uses_extracts_repo_sha_tag(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "example.yml").write_text(
        "steps:\n"
        "  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1\n",
        encoding="utf-8",
    )
    found = freshness._scan_pinned_uses(tmp_path)
    assert len(found) == 1
    assert found[0].repo == "actions/checkout"
    assert found[0].tag == "v7.0.1"
    assert found[0].file == ".github/workflows/example.yml"


def test_scan_pinned_uses_ignores_local_actions(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "example.yml").write_text(
        "steps:\n  - uses: ./.github/actions/uv-sync-retry\n",
        encoding="utf-8",
    )
    assert freshness._scan_pinned_uses(tmp_path) == []


def test_find_outdated_reports_newer_tag() -> None:
    pinned = [
        freshness.PinnedUse(
            repo="actions/checkout", sha="a" * 40, tag="v7.0.0", file="a.yml"
        )
    ]
    outdated = freshness._find_outdated(
        pinned, token=None, fetch_tags=lambda repo, token: ["v7.0.0", "v7.0.1"]
    )
    assert len(outdated) == 1
    assert outdated[0].latest_tag == "v7.0.1"
    assert outdated[0].files == ["a.yml"]


def test_find_outdated_skips_up_to_date_pins() -> None:
    pinned = [
        freshness.PinnedUse(
            repo="actions/checkout", sha="a" * 40, tag="v7.0.1", file="a.yml"
        )
    ]
    outdated = freshness._find_outdated(
        pinned, token=None, fetch_tags=lambda repo, token: ["v7.0.0", "v7.0.1"]
    )
    assert outdated == []


def test_find_outdated_skips_repo_when_fetch_fails() -> None:
    pinned = [
        freshness.PinnedUse(
            repo="actions/checkout", sha="a" * 40, tag="v7.0.0", file="a.yml"
        )
    ]

    def _boom(repo: str, token: str | None) -> list[str]:
        raise ValueError("boom")

    outdated = freshness._find_outdated(pinned, token=None, fetch_tags=_boom)
    assert outdated == []


def test_format_report_lists_outdated_actions() -> None:
    outdated = [
        freshness.OutdatedAction(
            repo="actions/checkout",
            pinned_tag="v7.0.0",
            latest_tag="v7.0.1",
            files=["a.yml"],
        )
    ]
    report = freshness._format_report(outdated)
    assert "actions/checkout" in report
    assert "v7.0.0" in report
    assert "v7.0.1" in report


def test_format_report_all_up_to_date() -> None:
    assert "latest" in freshness._format_report([])
