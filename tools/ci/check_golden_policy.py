#!/usr/bin/env python3
"""Enforce contract + golden snapshot policy for CI and local checks.

Policy (from .analysis/done/harden-contract-and-golden-testing/policy-matrix.md):
- If golden fixtures are unchanged: pass.
- If golden fixtures changed: require evidence fields and valid drift class.
- Drift class C requires an explicit governed change artifact path.
"""

from __future__ import annotations

import argparse
import os
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

GOLDEN_GLOB = "tests/contract/fixtures/*.golden.json"
ALLOWED_CLASSES = {"A", "B", "C"}
EVIDENCE_PATH_DEFAULT = ".analysis/review/golden-change-evidence.md"
ENFORCEMENT_MODES = {"warn", "block", "strict"}


@dataclass(frozen=True)
class Evaluation:
    ok: bool
    message: str


def _run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(  # nosec B603
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _changed_worktree_files() -> list[str]:
    code, out, _ = _run(["git", "status", "--porcelain", GOLDEN_GLOB])
    if code != 0:
        return []
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # porcelain format: XY <path>
        path = line[3:].strip()
        if path:
            files.append(path)
    return sorted(set(files))


def _changed_commit_files() -> list[str]:
    # Prefer PR-aware range if available.
    base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    if base_ref:
        _run(["git", "fetch", "--depth=100", "origin", base_ref])
        code, out, _ = _run(
            [
                "git",
                "diff",
                "--name-only",
                f"origin/{base_ref}...HEAD",
                "--",
                GOLDEN_GLOB,
            ]
        )
        if code == 0:
            return sorted({line.strip() for line in out.splitlines() if line.strip()})

    # Fallback to last commit diff (works in most local/CI contexts).
    code, out, _ = _run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", GOLDEN_GLOB]
    )
    if code == 0:
        return sorted({line.strip() for line in out.splitlines() if line.strip()})
    return []


def _parse_evidence(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not path.exists():
        return payload
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip().lower()] = value.strip()
    return payload


def _is_governed_change_artifact(path_text: str) -> bool:
    if not path_text:
        return False
    p = Path(path_text)
    if not p.exists():
        return False
    if p.is_file():
        return p.name in {"proposal.md", "design.md", "tasks.md", "spec.md"}
    # directory case: require at least proposal+tasks
    return (p / "proposal.md").exists() and (p / "tasks.md").exists()


def _report(result: Evaluation, mode: str) -> int:
    if result.ok:
        print(f"PASS: GOLDEN_POLICY_OK: {result.message}")
        return 0
    if mode == "warn":
        print(f"WARN: GOLDEN_POLICY_WARNING: {result.message}")
        return 0
    print(f"FAIL: GOLDEN_POLICY_VIOLATION: {result.message}")
    return 1


def _evaluate(changed: list[str], evidence: dict[str, str], mode: str) -> Evaluation:
    if not changed:
        return Evaluation(ok=True, message="no golden snapshot changes detected")

    drift_class = evidence.get("drift-class", "").upper()
    if drift_class not in ALLOWED_CLASSES:
        return Evaluation(ok=False, message="evidence must define 'Drift-Class: A|B|C'")
    if not evidence.get("rationale", ""):
        return Evaluation(ok=False, message="evidence must define 'Rationale: ...'")
    if not evidence.get("governing-artifact", ""):
        return Evaluation(
            ok=False,
            message="evidence must define 'Governing-Artifact: <path>'",
        )
    if not evidence.get("decision-owner", ""):
        return Evaluation(
            ok=False, message="evidence must define 'Decision-Owner: <name>'"
        )

    governed_path = evidence.get("governing-artifact", "")
    if drift_class == "C" and not _is_governed_change_artifact(governed_path):
        return Evaluation(
            ok=False,
            message=(
                "Drift-Class C requires a valid governed change artifact path "
                "(proposal/design/tasks/spec or change directory)."
            ),
        )

    reviewer_approval = evidence.get("reviewer-approval", "").strip()
    if (
        mode in {"block", "strict"}
        and drift_class in {"B", "C"}
        and not reviewer_approval
    ):
        return Evaluation(
            ok=False,
            message=(
                f"mode={mode} requires 'Reviewer-Approval: ...' for drift class {drift_class}"
            ),
        )
    if mode == "strict" and drift_class == "A" and not reviewer_approval:
        return Evaluation(
            ok=False,
            message="mode=strict requires 'Reviewer-Approval: ...' for any drift class",
        )

    return Evaluation(
        ok=True,
        message=(
            "golden changes include required evidence "
            f"(class={drift_class}, owner={evidence.get('decision-owner')}, mode={mode})"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate golden snapshot governance policy."
    )
    parser.add_argument(
        "--evidence-path",
        default=EVIDENCE_PATH_DEFAULT,
        help=f"Path to evidence note (default: {EVIDENCE_PATH_DEFAULT})",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(ENFORCEMENT_MODES),
        default=os.environ.get("SDD_GOLDEN_ENFORCEMENT_MODE", "block"),
        help=(
            "Progressive enforcement mode: warn|block|strict "
            "(default: env SDD_GOLDEN_ENFORCEMENT_MODE or block)"
        ),
    )
    args = parser.parse_args(argv)

    mode = (args.mode or "block").strip().lower()
    if mode not in ENFORCEMENT_MODES:
        print(f"FAIL: GOLDEN_POLICY_VIOLATION: invalid mode '{mode}'")
        return 1

    changed = sorted(set(_changed_worktree_files() + _changed_commit_files()))

    evidence_path = Path(args.evidence_path)
    evidence = _parse_evidence(evidence_path)
    if changed:
        print("Detected golden changes:")
        for f in changed:
            print(f"  - {f}")
        if not evidence:
            return _report(
                Evaluation(
                    ok=False,
                    message=(
                        "golden changes require evidence file with drift class and rationale. "
                        f"Expected: {evidence_path}"
                    ),
                ),
                mode,
            )

    result = _evaluate(changed, evidence, mode)
    return _report(result, mode)


if __name__ == "__main__":
    raise SystemExit(main())
