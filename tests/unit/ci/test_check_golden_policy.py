"""Unit tests for tools/ci/check_golden_policy.py."""

from __future__ import annotations

from pathlib import Path

from tools.ci import check_golden_policy as policy


def test_parse_evidence_reads_key_values(tmp_path: Path) -> None:
    p = tmp_path / "evidence.md"
    p.write_text(
        "\n".join(
            [
                "Drift-Class: B",
                "Rationale: intended schema extension",
                "Governing-Artifact: .analysis/plans/x/proposal.md",
                "Decision-Owner: reviewer",
            ]
        ),
        encoding="utf-8",
    )
    data = policy._parse_evidence(p)
    assert data["drift-class"] == "B"
    assert data["decision-owner"] == "reviewer"


def test_governed_artifact_accepts_change_dir(tmp_path: Path) -> None:
    change = tmp_path / "change-a"
    change.mkdir()
    (change / "proposal.md").write_text("x", encoding="utf-8")
    (change / "tasks.md").write_text("x", encoding="utf-8")
    assert policy._is_governed_change_artifact(str(change)) is True


def test_governed_artifact_rejects_missing_path(tmp_path: Path) -> None:
    assert policy._is_governed_change_artifact(str(tmp_path / "missing")) is False


def test_evaluate_warn_allows_missing_evidence() -> None:
    result = policy._evaluate(["tests/contract/fixtures/x.golden.json"], {}, "warn")
    assert result.ok is False
    assert "Drift-Class" in result.message


def test_evaluate_block_requires_reviewer_for_class_b(tmp_path: Path) -> None:
    proposal = tmp_path / "proposal.md"
    proposal.write_text("x", encoding="utf-8")
    evidence = {
        "drift-class": "B",
        "rationale": "compatible extension",
        "governing-artifact": str(proposal),
        "decision-owner": "reviewer",
    }
    result = policy._evaluate(
        ["tests/contract/fixtures/x.golden.json"], evidence, "block"
    )
    assert result.ok is False
    assert "Reviewer-Approval" in result.message


def test_evaluate_block_accepts_reviewer_for_class_b(tmp_path: Path) -> None:
    proposal = tmp_path / "proposal.md"
    proposal.write_text("x", encoding="utf-8")
    evidence = {
        "drift-class": "B",
        "rationale": "compatible extension",
        "governing-artifact": str(proposal),
        "decision-owner": "reviewer",
        "reviewer-approval": "yes",
    }
    result = policy._evaluate(
        ["tests/contract/fixtures/x.golden.json"], evidence, "block"
    )
    assert result.ok is True


def test_evaluate_strict_requires_reviewer_even_for_class_a(tmp_path: Path) -> None:
    proposal = tmp_path / "proposal.md"
    proposal.write_text("x", encoding="utf-8")
    evidence = {
        "drift-class": "A",
        "rationale": "timestamp noise only",
        "governing-artifact": str(proposal),
        "decision-owner": "reviewer",
    }
    result = policy._evaluate(
        ["tests/contract/fixtures/x.golden.json"], evidence, "strict"
    )
    assert result.ok is False
    assert "mode=strict" in result.message
