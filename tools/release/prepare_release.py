#!/usr/bin/env python3
"""Insert a CHANGELOG.md version header and update README.md's pinned install tag.

Run locally before creating a release tag (`git tag vX.Y.Z`), as an automated
first step of the manual Release Checklist documented in CHANGELOG.md. Does
not commit, tag, or push — review the resulting `git diff`, then commit and
tag by hand, same as every other step in that checklist.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Repo root is two levels up from tools/release/, matching the sibling
# scripts in this package (resolve_vcs_version.py, validate_release_assets.py).
REPO_ROOT = Path(__file__).resolve().parents[2]

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_UNRELEASED_HEADER = "## [Unreleased]"
_VERSION_HEADER_RE = re.compile(r"^## \[(?P<version>[^\]]+)\]")

# Anchored to the specific git-subdirectory install snippet in README.md,
# not a blind repo-wide version regex — see design.md in
# .analysis/refined/20260825-changelog-readme-automation/.
_README_PROSE_RE = re.compile(r"Replace `v(?P<version>\d+\.\d+\.\d+)`")
_README_INSTALL_RE = re.compile(r"@v(?P<version>\d+\.\d+\.\d+)#subdirectory=")


class PrepareReleaseError(ValueError):
    """Raised when CHANGELOG.md or README.md do not match the expected shape."""


@dataclass
class PrepareResult:
    changelog_path: Path
    readme_path: Path
    version: str
    changelog_header_inserted: bool
    readme_updated: bool


def _validate_version(version: str) -> str:
    if not _VERSION_RE.match(version):
        raise PrepareReleaseError(
            f"invalid version {version!r} (expected X.Y.Z, no 'v' prefix)"
        )
    return version


def prepare_changelog(changelog_path: Path, version: str, *, today: date) -> bool:
    """Insert ``## [<version>] — <today>`` under ``[Unreleased]``, moving its body down.

    Leaves ``[Unreleased]`` present but empty above the new section, per the
    Keep a Changelog convention this file already documents.

    Returns True if a header was inserted, False if a section for this
    version already exists (idempotent no-op — never duplicates).
    """
    lines = changelog_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        match = _VERSION_HEADER_RE.match(line)
        if match and match.group("version") == version:
            return False

    try:
        unreleased_idx = next(
            i for i, line in enumerate(lines) if line.strip() == _UNRELEASED_HEADER
        )
    except StopIteration as exc:
        raise PrepareReleaseError(
            f"'{_UNRELEASED_HEADER}' header not found in {changelog_path}"
        ) from exc

    next_header_idx = next(
        (
            i
            for i in range(unreleased_idx + 1, len(lines))
            if _VERSION_HEADER_RE.match(lines[i])
        ),
        len(lines),
    )
    body = lines[unreleased_idx + 1 : next_header_idx]

    if not any(line.strip() for line in body):
        raise PrepareReleaseError(
            f"'{_UNRELEASED_HEADER}' has no entries — add changelog notes under "
            f"'{_UNRELEASED_HEADER}' before preparing version {version}. "
            "release.yml's changelog-extraction step rejects a version section "
            "with no content between it and the next header, even though the "
            "header itself would exist."
        )

    new_section = [
        _UNRELEASED_HEADER,
        "",
        f"## [{version}] — {today.isoformat()}",
        *body,
    ]
    lines[unreleased_idx:next_header_idx] = new_section
    changelog_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def prepare_readme(readme_path: Path, version: str) -> bool:
    """Replace the pinned install-tag references in README.md with ``version``.

    Returns True if the file content changed, False if it already matched
    (safe no-op on a re-run).
    """
    text = readme_path.read_text(encoding="utf-8")

    if _README_PROSE_RE.search(text) is None or _README_INSTALL_RE.search(text) is None:
        raise PrepareReleaseError(
            f"expected pinned-tag anchors not found in {readme_path} "
            "(prose 'Replace `vX.Y.Z`' and install '@vX.Y.Z#subdirectory=') — "
            "the file structure may have changed since this script was written"
        )

    new_text = _README_PROSE_RE.sub(f"Replace `v{version}`", text, count=1)
    new_text = _README_INSTALL_RE.sub(f"@v{version}#subdirectory=", new_text, count=1)

    if new_text == text:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
    return True


def prepare_release(
    version: str,
    *,
    changelog_path: Path,
    readme_path: Path,
    today: date | None = None,
) -> PrepareResult:
    version = _validate_version(version)
    resolved_today = today or date.today()
    changelog_inserted = prepare_changelog(
        changelog_path, version, today=resolved_today
    )
    readme_updated = prepare_readme(readme_path, version)
    return PrepareResult(
        changelog_path=changelog_path,
        readme_path=readme_path,
        version=version,
        changelog_header_inserted=changelog_inserted,
        readme_updated=readme_updated,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Insert a CHANGELOG.md version header and update README.md's "
            "pinned install tag, ahead of creating a release tag."
        )
    )
    parser.add_argument(
        "--version",
        required=True,
        help="target release version, without the 'v' prefix (e.g. 1.0.11)",
    )
    args = parser.parse_args(argv)

    try:
        result = prepare_release(
            args.version,
            changelog_path=REPO_ROOT / "CHANGELOG.md",
            readme_path=REPO_ROOT / "README.md",
        )
    except PrepareReleaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result.changelog_header_inserted:
        print(f"CHANGELOG.md: inserted '## [{result.version}]' section")
    else:
        print(f"CHANGELOG.md: '## [{result.version}]' section already present (no-op)")

    if result.readme_updated:
        print(f"README.md: pinned install tag updated to v{result.version}")
    else:
        print(f"README.md: already pinned to v{result.version} (no-op)")

    print("\nReview the diff, then commit and tag manually:")
    print("  git diff -- CHANGELOG.md README.md")
    print(
        "  git add CHANGELOG.md README.md && "
        f"git commit -m 'chore: prepare release v{result.version}'"
    )
    print(f"  git tag v{result.version} && git push origin v{result.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
