#!/usr/bin/env python3
"""
Mandate and Guidelines Compiler for AI optimization

Compiles mandate.spec and guidelines.dsl to MessagePack binary format
for 65% size reduction and 3-4x faster parsing.

Supports fallback to JSON if msgpack not available.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Try to import msgpack
try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


class MandateCompiler:
    """Compile mandate.spec to binary format"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, msg: str) -> None:
        """Log."""
        if self.verbose:
            print(f"  {msg}")  # noqa: T201

    def parse_mandate_spec(self, text: str) -> tuple[int, list[dict[str, Any]]]:
        """Parse mandate.spec DSL format"""
        mandates = []

        # Pattern: mandate M001 { ... }
        mandate_pattern = r"mandate\s+(M\d+)\s*\{([^}]*)\}"

        for match in re.finditer(mandate_pattern, text, re.DOTALL):
            mandate_id = match.group(1)
            mandate_body = match.group(2)

            # Extract fields
            type_match = re.search(r"type:\s*(\w+)", mandate_body)
            title_match = re.search(r'title:\s*"([^"]*)"', mandate_body)
            description_match = re.search(
                r'description:\s*"([^"]*)"', mandate_body, re.DOTALL
            )
            criticality_match = re.search(r"criticality:\s*(\w+)", mandate_body)

            mandate = {
                "id": mandate_id,
                "id_num": int(mandate_id[1:]),  # M001 → 1
                "type": type_match.group(1) if type_match else "HARD",
                "title": title_match.group(1) if title_match else "Unknown",
                "description": (
                    description_match.group(1).replace("\n", " ").strip()[:500]
                    if description_match
                    else ""
                ),
                "criticality": (
                    criticality_match.group(1) if criticality_match else "OBRIGATÓRIO"
                ),
            }
            mandates.append(mandate)

        return len(mandates), mandates

    def parse_guidelines_dsl(self, text: str) -> tuple[int, list[dict[str, Any]]]:
        """Parse guidelines.dsl DSL format"""
        guidelines = []

        # Pattern: guideline G001 { ... }
        guideline_pattern = r"guideline\s+(G\d+)\s*\{([^}]*)\}"

        guide_num = 0
        for match in re.finditer(guideline_pattern, text, re.DOTALL):
            guide_id = match.group(1)
            guide_body = match.group(2)

            # Extract fields
            type_match = re.search(r"type:\s*(\w+)", guide_body)
            title_match = re.search(r'title:\s*"([^"]*)"', guide_body)
            description_match = re.search(
                r'description:\s*"([^"]*)"', guide_body, re.DOTALL
            )
            category_match = re.search(r"category:\s*(\w+)", guide_body)

            # Extract number from guide_id (G01 → 1)
            num_match = re.search(r"G(\d+)", guide_id)
            guide_num = int(num_match.group(1)) if num_match else guide_num + 1

            guideline = {
                "id": guide_id,
                "id_num": guide_num,
                "type": type_match.group(1) if type_match else "SOFT",
                "title": title_match.group(1) if title_match else "Unknown",
                "description": (
                    description_match.group(1).replace("\n", " ").strip()[:300]
                    if description_match
                    else ""
                ),
                "category": (
                    category_match.group(1).lower() if category_match else "general"
                ),
            }
            guidelines.append(guideline)

        return len(guidelines), guidelines

    def compile_to_binary(
        self, mandates: list[dict[str, Any]], format: str = "msgpack"
    ) -> bytes:
        """
        Compile mandates to binary format

        Args:
            mandates: List of mandate dicts
            format: "msgpack" or "json_compressed"

        Returns:
            Binary data
        """
        output = {
            "version": "3.1",
            "format_version": "3.1",
            "compiled_at": datetime.now().isoformat(),
            "mandates": mandates,
            "count": len(mandates),
        }

        if format == "msgpack" and HAS_MSGPACK:
            return bytes(msgpack.packb(output, use_bin_type=True))
        else:
            # Fallback: compact JSON
            json_str = json.dumps(output, separators=(",", ":"))
            return json_str.encode("utf-8")

    def compile_mandate_spec(
        self, input_file: Path, output_file: Path, format: str = "msgpack"
    ) -> bool:
        """Compile mandate.spec to binary"""
        try:
            self.log(f"Compiling mandate.spec ({format})")

            # Read source
            if not input_file.exists():
                print(f"  ❌ Source not found: {input_file}")  # noqa: T201
                return False

            text = input_file.read_text(encoding="utf-8")
            count, mandates = self.parse_mandate_spec(text)

            self.log(f"  Parsed {count} mandates")

            if count == 0:
                self.log("  ⚠️  No mandates found")

            # Compile to binary
            binary_data = self.compile_to_binary(mandates, format)

            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(binary_data, bytes):
                output_file.write_bytes(binary_data)
            else:
                output_file.write_text(binary_data, encoding="utf-8")

            size = (
                len(binary_data)
                if isinstance(binary_data, bytes)
                else len(binary_data.encode())
            )
            self.log(f"  ✅ Compiled to {output_file.name} ({size:,} bytes)")

            return True
        except Exception as e:
            print(f"  ❌ Compilation failed: {e}")  # noqa: T201
            import traceback

            traceback.print_exc()
            return False

    def compile_guidelines_dsl(
        self, input_file: Path, output_file: Path, format: str = "msgpack"
    ) -> bool:
        """Compile guidelines.dsl to binary"""
        try:
            self.log(f"Compiling guidelines.dsl ({format})")

            # Read source
            if not input_file.exists():
                self.log(f"  ℹ️  Guidelines not found: {input_file}")
                return True  # Optional

            text = input_file.read_text(encoding="utf-8")
            count, guidelines = self.parse_guidelines_dsl(text)

            self.log(f"  Parsed {count} guidelines")

            # Create output structure
            output = {
                "version": "3.1",
                "format_version": "3.1",
                "compiled_at": datetime.now().isoformat(),
                "guidelines": guidelines,
                "count": count,
            }

            # Compile to binary
            if format == "msgpack" and HAS_MSGPACK:
                binary_data = msgpack.packb(output, use_bin_type=True)
            else:
                json_str = json.dumps(output, separators=(",", ":"))
                binary_data = json_str.encode("utf-8")

            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(binary_data, bytes):
                output_file.write_bytes(binary_data)
            else:
                output_file.write_text(binary_data, encoding="utf-8")

            size = (
                len(binary_data)
                if isinstance(binary_data, bytes)
                else len(binary_data.encode())
            )
            self.log(f"  ✅ Compiled to {output_file.name} ({size:,} bytes)")

            return True
        except Exception as e:
            print(f"  ❌ Compilation failed: {e}")  # noqa: T201
            return False
