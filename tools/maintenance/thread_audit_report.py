#!/usr/bin/env python3
"""Generate a static thread-risk audit report for production code."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "packages"
OUTPUT_FILE = REPO_ROOT / "docs" / "guides" / "THREAD_AUDIT_REPORT.md"


@dataclass(frozen=True)
class Finding:
    priority: str
    file_path: str
    line: int
    rule: str
    snippet: str


def _priority_for(rule: str) -> str:
    if rule in {"daemon-thread", "bare-lock-with-shared-state"}:
        return "P0"
    if rule in {"thread-start", "rlock-usage"}:
        return "P1"
    return "P2"


def _iter_py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "tests" not in p.parts)


def _snippet(lines: list[str], lineno: int) -> str:
    if lineno < 1 or lineno > len(lines):
        return ""
    return lines[lineno - 1].strip()


def _analyze_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)
    rel = str(path.relative_to(REPO_ROOT))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "Thread":
                is_daemon = any(
                    kw.arg == "daemon"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                    for kw in node.keywords
                )
                rule = "daemon-thread" if is_daemon else "thread-start"
                findings.append(
                    Finding(
                        priority=_priority_for(rule),
                        file_path=rel,
                        line=node.lineno,
                        rule=rule,
                        snippet=_snippet(lines, node.lineno),
                    )
                )
            if node.func.attr == "RLock":
                rule = "rlock-usage"
                findings.append(
                    Finding(
                        priority=_priority_for(rule),
                        file_path=rel,
                        line=node.lineno,
                        rule=rule,
                        snippet=_snippet(lines, node.lineno),
                    )
                )
            if node.func.attr == "Lock":
                rule = "bare-lock-with-shared-state"
                findings.append(
                    Finding(
                        priority=_priority_for(rule),
                        file_path=rel,
                        line=node.lineno,
                        rule=rule,
                        snippet=_snippet(lines, node.lineno),
                    )
                )
    return findings


def _render(findings: list[Finding]) -> str:
    p0 = [f for f in findings if f.priority == "P0"]
    p1 = [f for f in findings if f.priority == "P1"]
    p2 = [f for f in findings if f.priority == "P2"]
    lines = [
        "# Thread Audit Report",
        "",
        "Static audit of `threading` hotspots in production modules.",
        "",
        f"- Findings: {len(findings)}",
        f"- P0: {len(p0)}",
        f"- P1: {len(p1)}",
        f"- P2: {len(p2)}",
        "",
        "## Findings",
        "",
        "| Priority | File | Line | Rule | Snippet |",
        "|---|---|---:|---|---|",
    ]
    for item in sorted(findings, key=lambda x: (x.priority, x.file_path, x.line)):
        lines.append(
            f"| {item.priority} | `{item.file_path}` | {item.line} | `{item.rule}` | `{item.snippet}` |"
        )
    if not findings:
        lines.append("| - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Priority Rules",
            "",
            "- `P0`: daemon thread lifecycle risk or broad lock scope needing explicit shutdown checks.",
            "- `P1`: explicit thread creation / RLock usage requiring deterministic lifecycle tests.",
            "- `P2`: lower-risk patterns requiring documentation and periodic review.",
            "",
            "## Regeneration",
            "",
            "```bash",
            "uv run python tools/maintenance/thread_audit_report.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    findings: list[Finding] = []
    for file_path in _iter_py_files(PACKAGES_DIR):
        findings.extend(_analyze_file(file_path))
    OUTPUT_FILE.write_text(_render(findings), encoding="utf-8")
    print(f"wrote {OUTPUT_FILE} ({len(findings)} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
