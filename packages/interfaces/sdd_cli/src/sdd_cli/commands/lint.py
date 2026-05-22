"""Lint."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

import typer

from sdd_cli.utils.command_errors import handle_cli_errors

app = typer.Typer()


@app.callback()
def _() -> None:
    """Run lint checks."""


def _run_step(label: str, cmd: list[str], *, fix: bool) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()

    typer.echo(f"\nRunning: {label}")
    result = runner.run(cmd)
    if not result.success:
        if fix:
            typer.echo(f"  WARN: {label} reported issues (auto-fix attempted)")
        else:
            typer.echo(f"  ERROR: {label} failed")
    else:
        typer.echo(f"  OK: {label} OK")
    return result.returncode


def _slugify_anchor(value: str) -> str:
    """Generate a stable slug comparable with markdown heading anchors."""
    text = unquote(value).strip().lstrip("#").lower()
    text = re.sub(r"\{#([A-Za-z0-9._:-]+)\}\s*$", "", text).strip()
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "")
    text = text.replace("*", "")
    text = text.replace("_", "")
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text


def _extract_file_anchors(file_path: Path) -> set[str]:
    """Extract all valid anchors from markdown headings and explicit IDs."""
    anchors: set[str] = set()
    content = file_path.read_text(encoding="utf-8")

    for explicit_id in re.findall(r"\{#([A-Za-z0-9._:-]+)\}", content):
        anchors.add(explicit_id.strip().lower())

    in_fenced_code = False
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue

        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue

        heading = re.sub(r"\s+#+\s*$", "", match.group(1)).strip()
        explicit_match = re.search(r"\{#([A-Za-z0-9._:-]+)\}\s*$", heading)
        if explicit_match:
            anchors.add(explicit_match.group(1).strip().lower())
            heading = re.sub(r"\s*\{#[A-Za-z0-9._:-]+\}\s*$", "", heading).strip()

        slug = _slugify_anchor(heading)
        if slug:
            anchors.add(slug)

    return anchors


def _filter_code_blocks(content: str) -> list[str]:
    """Return content lines with fenced code block interiors blanked out (preserves line count)."""
    in_fenced_code = False
    filtered_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_code = not in_fenced_code
            filtered_lines.append(line)
            continue
        if in_fenced_code:
            filtered_lines.append("")
            continue
        filtered_lines.append(line)
    return filtered_lines


def _resolve_link_target(source_file: Path, raw_target: str) -> tuple[Path, str] | None:
    """Resolve a raw markdown link target to (target_file, fragment) or None if it should be skipped."""
    if not raw_target:
        return None

    if raw_target.startswith("<") and raw_target.endswith(">"):
        raw_target = raw_target[1:-1]

    target = raw_target.split()[0]
    if target.startswith(("http://", "https://", "mailto:", "tel:")):
        return None

    if target.startswith("#"):
        return source_file, target[1:]

    if "#" in target:
        rel_path, fragment = target.split("#", 1)
    else:
        rel_path, fragment = target, ""

    candidate = (source_file.parent / unquote(rel_path)).resolve()
    if not candidate.exists():
        return None
    return candidate, fragment


def _validate_markdown_anchors(markdown_files: list[Path], repo_root: Path) -> int:
    """Validate local markdown links and anchor fragments."""
    errors = 0
    anchors_cache: dict[Path, set[str]] = {}
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for source_file in markdown_files:
        filtered_content = "\n".join(
            _filter_code_blocks(source_file.read_text(encoding="utf-8"))
        )
        for match in link_pattern.finditer(filtered_content):
            result = _resolve_link_target(source_file, match.group(1).strip())
            if result is None:
                continue
            target_file, fragment = result
            if not fragment:
                continue
            if target_file not in anchors_cache:
                anchors_cache[target_file] = _extract_file_anchors(target_file)
            normalized = _slugify_anchor(fragment)
            anchors = anchors_cache[target_file]
            if (
                normalized
                and normalized not in anchors
                and unquote(fragment).lower() not in anchors
            ):
                typer.echo(
                    f"  ❌ {source_file.relative_to(repo_root)}: "
                    f"anchor '#{fragment}' not found in {target_file.relative_to(repo_root)}"
                )
                errors += 1

    return errors


def _validate_link_fragment_style(
    source_file: Path, raw_target: str, repo_root: Path
) -> int:
    """Validate a single link's fragment for style violations. Returns 0 or 1 error count."""
    if not raw_target:
        return 0
    target = raw_target.split()[0]
    if target.startswith(("http://", "https://", "mailto:", "tel:")):
        return 0
    fragment = ""
    if target.startswith("#"):
        fragment = target[1:]
    elif "#" in target:
        _, fragment = target.split("#", 1)
    if not fragment:
        return 0
    if "%" in fragment:
        typer.echo(
            f"  ❌ {source_file.relative_to(repo_root)}: URL-encoded anchor fragment '#{fragment}' is not allowed"
        )
        return 1
    if not _slugify_anchor(fragment):
        typer.echo(
            f"  ❌ {source_file.relative_to(repo_root)}: anchor fragment '#{fragment}' resolves to empty slug"
        )
        return 1
    return 0


def _validate_anchor_style(markdown_files: list[Path], repo_root: Path) -> int:
    """Validate fragile or non-standard anchor usage patterns."""
    errors = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for source_file in markdown_files:
        filtered_lines = _filter_code_blocks(source_file.read_text(encoding="utf-8"))
        filtered_content = "\n".join(filtered_lines)

        for match in link_pattern.finditer(filtered_content):
            errors += _validate_link_fragment_style(
                source_file, match.group(1).strip(), repo_root
            )

        for line_number, line in enumerate(filtered_lines, start=1):
            if re.match(r"^#{1,6}\s+", line) and line.rstrip() != line:
                typer.echo(
                    f"  ❌ {source_file.relative_to(repo_root)}:{line_number}: "
                    "heading has trailing whitespace, which can destabilize generated anchors"
                )
                errors += 1

    return errors


def _collect_active_markdown_files(repo_root: Path) -> list[Path]:
    """Collect markdown files from active docs scope and main entry docs."""
    files = set()

    docs_dir = repo_root / "docs"
    if docs_dir.exists():
        for file in docs_dir.rglob("*.md"):
            if "archive" in file.parts:
                continue
            files.add(file.resolve())

    for name in ("README.md", "readme-detailed.md", "readme-client.md"):
        candidate = repo_root / name
        if candidate.exists():
            files.add(candidate.resolve())

    return sorted(files)


def _check_legacy_patterns(canonical_dir: Path, repo_root: Path) -> int:
    """Check for legacy path references in canonical docs. Returns error count."""
    patterns = [
        (re.compile(r"docs/specs"), "Legacy 'docs/specs' used (should be docs/spec)"),
        (re.compile(r"(?<!\.sdd)/runtime/"), "Legacy '/runtime/' reference"),
        (re.compile(r"/REALITY/"), "Legacy '/REALITY/' reference"),
        (re.compile(r"/DEVELOPMENT/"), "Legacy '/DEVELOPMENT/' reference"),
        (re.compile(r"sdd-generated"), "Legacy 'sdd-generated' reference"),
    ]
    errors = 0
    for file in canonical_dir.rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        for pattern, msg in patterns:
            if pattern.search(content):
                typer.echo(f"  ❌ {file.relative_to(repo_root)}: {msg}")
                errors += 1
    return errors


def _check_project_leaks(canonical_dir: Path, repo_root: Path) -> int:
    """Check for project-specific identifier leaks in canonical core docs. Returns error count."""
    patterns = [
        (re.compile(r"rpg-narrative-server"), "Project leak: rpg-narrative-server"),
        (re.compile(r"game-master"), "Project leak: game-master"),
    ]
    errors = 0
    for file in (canonical_dir / "core").rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        for pattern, msg in patterns:
            if pattern.search(content):
                typer.echo(f"  ❌ {file.relative_to(repo_root)}: {msg}")
                errors += 1
    return errors


def _collect_anchor_files(repo_root: Path, validate_all_anchors: bool) -> list[Path]:
    """Collect markdown files for anchor validation based on scope flag."""
    if validate_all_anchors:
        files = _collect_active_markdown_files(repo_root)
        typer.echo(
            f"🔗 Checking markdown anchors in active docs scope ({len(files)} files)..."
        )
        return files
    wizard_docs_dir = (
        repo_root / "docs" / "spec" / "reality" / "implementation-analyses" / "wizard"
    )
    if not wizard_docs_dir.exists():
        return []
    candidates = [
        wizard_docs_dir / "START_HERE_FOR_DOCUMENTATION.md",
        wizard_docs_dir / "WIZARD_DOCUMENTATION_INDEX.md",
    ]
    files = [f for f in candidates if f.exists()]
    if files:
        typer.echo("🔗 Checking markdown anchors in wizard entry docs...")
    return files


@app.command()
def spec(
    validate_all_anchors: bool = typer.Option(
        True,
        "--validate-all-anchors/--validate-entry-anchors",
        help="Validate anchors on all active documentation files (excluding docs/archive)",
    ),
    strict_anchor_style: bool = typer.Option(
        True,
        "--strict-anchor-style/--no-strict-anchor-style",
        help="Fail on fragile anchor patterns such as URL-encoded fragments",
    ),
) -> None:
    """Check documentation structure and canonical paths."""
    from sdd_cli.utils.environment import detect_repo_root

    repo_root = detect_repo_root()
    canonical_dir = repo_root / "docs" / "spec" / "canonical"

    if not canonical_dir.exists():
        typer.echo(f"  ERROR: Canonical directory not found: {canonical_dir}")
        raise typer.Exit(1)

    typer.echo(f"🔍 Checking canonical documentation in {canonical_dir}...")
    errors = _check_legacy_patterns(canonical_dir, repo_root)
    errors += _check_project_leaks(canonical_dir, repo_root)

    anchor_files = _collect_anchor_files(repo_root, validate_all_anchors)
    if anchor_files:
        errors += _validate_markdown_anchors(anchor_files, repo_root)
        if strict_anchor_style:
            errors += _validate_anchor_style(anchor_files, repo_root)

    if errors > 0:
        typer.echo(f"\n❌ Spec linting failed with {errors} errors")
        raise typer.Exit(1)

    typer.echo("✅ Spec structure OK")


def _run_ruff(fix: bool) -> bool:
    """Run ruff check + format. Returns True if anything failed (unfixed)."""
    ruff_cmd = [sys.executable, "-m", "ruff", "check", "."]
    if fix:
        ruff_cmd += ["--fix", "--unsafe-fixes"]
    check_failed = _run_step("ruff", ruff_cmd, fix=fix) != 0 and not fix
    if check_failed:
        typer.echo(
            "  HINT: Ruff includes F401 (unused imports). Remove dead imports or move type-only imports under TYPE_CHECKING."
        )

    fmt_cmd = [sys.executable, "-m", "ruff", "format", "."]
    if not fix:
        fmt_cmd.append("--check")
    fmt_failed = _run_step("ruff format", fmt_cmd, fix=fix) != 0 and not fix

    return check_failed or fmt_failed


@app.command()
@handle_cli_errors(command_name="lint run")
def run(
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-fix ruff lint and format issues (includes unsafe fixes)",
    ),
    skip_mypy: bool = typer.Option(
        False, "--skip-mypy", help="Skip mypy type checking"
    ),
    skip_bandit: bool = typer.Option(
        False, "--skip-bandit", help="Skip bandit security checks"
    ),
    skip_spec: bool = typer.Option(
        False, "--skip-spec", help="Skip spec structure linting"
    ),
) -> None:
    """Run all lint checks: ruff, architecture, mypy, bandit, spec."""
    failed = _run_ruff(fix)

    if (
        _run_step(
            "architecture imports",
            [sys.executable, "tools/architecture/validate_imports.py"],
            fix=False,
        )
        != 0
    ):
        failed = True

    if (
        _run_step(
            "architecture cycles",
            [sys.executable, "tools/architecture/validate_cycles.py"],
            fix=False,
        )
        != 0
    ):
        failed = True

    if (
        _run_step(
            "architecture class-size",
            [
                sys.executable,
                "tools/architecture/validate_class_size.py",
                "--show-module-warnings",
            ],
            fix=False,
        )
        != 0
    ):
        failed = True

    if (
        _run_step(
            "cognitive governance",
            [sys.executable, "tools/governance/validate_cognitive_governance.py"],
            fix=False,
        )
        != 0
    ):
        failed = True

    if (
        not skip_mypy
        and _run_step("mypy", [sys.executable, "-m", "mypy", "."], fix=False) != 0
    ):
        failed = True

    if not skip_bandit:
        bandit_cmd = [sys.executable, "-m", "bandit", "-r", "packages/", "-ll", "-q"]
        if _run_step("bandit", bandit_cmd, fix=False) != 0:
            failed = True

    if not skip_spec:
        spec()

    if failed:
        raise typer.Exit(1)
