"""Spec Validator."""

from pathlib import Path
from typing import Any

import yaml


class SpecValidator:
    """SpecValidator."""

    def __init__(self, rules_path: str) -> None:
        self.rules: dict[str, Any] = yaml.safe_load(
            Path(rules_path).read_text(encoding="utf-8")
        )

    def validate(self, specs_root: Path) -> list[str]:
        """Validate."""
        errors: list[str] = []

        for spec_dir in specs_root.iterdir():
            if not spec_dir.is_dir():
                continue

            files = [f.name for f in spec_dir.glob("*.md")]

            # Rule: must have test-cases
            if (
                self.rules["spec_integrity"]["require_test_cases"]
                and "test-cases.md" not in files
            ):
                errors.append(f"{spec_dir}: missing test-cases.md")

            # Rule: separation IS vs SHOULD (simplificado)
            if self.rules["spec_integrity"]["require_separation_is_should"]:
                content = "\n".join(
                    f.read_text(encoding="utf-8") for f in spec_dir.glob("*.md")
                )
                if "current" in content.lower() and "must" in content.lower():
                    errors.append(f"{spec_dir}: possible IS/SHOULD mixing detected")

        return errors


if __name__ == "__main__":
    validator = SpecValidator("docs/ia/governance/canonical_rules.yaml")
    result = validator.validate(Path("specs"))

    if result:
        print("❌ Spec validation errors:")  # noqa: T201
        for e in result:
            print("-", e)  # noqa: T201
    else:
        print("✅ Specs are valid")  # noqa: T201
