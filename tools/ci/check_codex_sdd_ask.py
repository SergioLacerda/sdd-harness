from __future__ import annotations

from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    codex_dir = root / ".codex"
    if not codex_dir.exists():
        print("Codex prompt compliance skipped: .codex directory not present.")
        return 0

    command_surface = codex_dir / "commands.md"
    missing: list[str] = []
    checked = 0

    if not command_surface.exists():
        missing.append(f"{command_surface}: file missing")
    else:
        checked += 1
        if "sdd-ask" not in _read(command_surface):
            missing.append(f"{command_surface}: missing 'sdd-ask' anchor")

    if checked == 0:
        print("Codex prompt compliance skipped: no relevant Codex prompt files found.")
        return 0

    if missing:
        print("Codex prompt compliance failed. Missing sdd-ask anchors:")
        for item in missing:
            print(f" - {item}")
        return 1

    print("Codex prompt compliance passed: sdd-ask present in required files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
