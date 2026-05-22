"""
Pipeline builder for governance artifacts.

Orchestrates parsing and fingerprinting of governance specifications
from multiple formats (v3.0 Markdown, legacy DSL).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sdd_integration.builders.governance.fingerprinter import GovernanceFingerprinter
from sdd_integration.builders.governance.legacy_parser import LegacySpecParser
from sdd_integration.builders.governance.markdown_parser import MarkdownParser


class PipelineBuilder:
    """Builds governance artifacts from source specifications with deterministic hashing."""

    # Architectural constants for data schema
    SCHEMA_VERSION = "3.0"
    CORE_KEY = "governance_core"
    CLIENT_KEY = "governance_client"
    HASH_ALGORITHM = "sha256"

    def __init__(
        self,
        spec_path: str,
        parsed_items: dict[str, list[dict[str, Any]]] | None = None,
    ):
        self.spec_path = Path(spec_path)
        self.parsed_items = parsed_items or {"mandates": [], "guidelines": []}
        self.core_items: list[dict[str, Any]] = []
        self.client_items: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {}

    def build(self) -> dict[str, Any]:
        """Parses source files and generates deterministic fingerprints.

        Supports both v3.0 Markdown format (mandate.md / guidelines.md)
        and legacy DSL format (mandate.spec / guidelines.dsl).
        """
        # Priority path: when wizard provides parsed items from phase-2-input,
        # compile from those items directly to respect user selections.
        parsed_mandates = self.parsed_items.get("mandates", [])
        parsed_guidelines = self.parsed_items.get("guidelines", [])
        if parsed_mandates or parsed_guidelines:
            self.core_items = [
                {
                    "id": item.get("id", ""),
                    "type": "MANDATE",
                    "title": item.get("title", ""),
                    "status": item.get("status", "required"),
                    "criticality": item.get(
                        "criticality", "high"
                    ),  # Default: mandates are high criticality
                }
                for item in sorted(parsed_mandates, key=lambda i: i.get("id", ""))
                if item.get("id")
            ]
            self.client_items = [
                {
                    "id": item.get("id", ""),
                    "type": "GUIDELINE",
                    "title": item.get("title", ""),
                    "status": item.get("status", "required"),
                    "criticality": item.get(
                        "criticality", "medium"
                    ),  # Default: guidelines are medium criticality
                }
                for item in sorted(parsed_guidelines, key=lambda i: i.get("id", ""))
                if item.get("id")
            ]

            core_fingerprint = GovernanceFingerprinter.generate(self.core_items)
            client_fingerprint = GovernanceFingerprinter.generate(
                self.client_items, salt=core_fingerprint
            )

            self.result = {
                self.CORE_KEY: {
                    "fingerprint": core_fingerprint,
                    "version": self.SCHEMA_VERSION,
                },
                self.CLIENT_KEY: {
                    "fingerprint": client_fingerprint,
                    "fingerprint_core_salt": core_fingerprint,
                    "version": self.SCHEMA_VERSION,
                },
                "core_items": self.core_items,
                "client_items": self.client_items,
            }
            return self.result

        # Resolve path resilience: check for meta/ or mandates/ subdirectory
        spec_root = self.spec_path
        if (
            not (spec_root / "mandate.md").exists()
            and not (spec_root / "mandate.spec").exists()
        ) and (spec_root / "meta").exists():
            spec_root = spec_root / "meta"

        # Also check for mandates/mandates.md (v3.0 structure)
        if (
            not (spec_root / "mandate.md").exists()
            and (spec_root / "mandates" / "mandates.md").exists()
        ):
            md_mandate = spec_root / "mandates" / "mandates.md"
        else:
            md_mandate = spec_root / "mandate.md"

        legacy_mandate = spec_root / "mandate.spec"

        if md_mandate.exists():
            mandate_content = md_mandate.read_text(encoding="utf-8")
            # Parse Markdown headings: `# M001: Title` or `## M001 Title`
            md_ids = re.findall(r"^#{1,3}\s+(M\d+)[:\s]", mandate_content, re.MULTILINE)
            self.core_items = [
                {
                    "id": mid,
                    "type": "MANDATE",
                    "title": MarkdownParser.extract_summary_minimal(
                        mandate_content, mid
                    )
                    or mid,
                    "status": "active",
                    "criticality": "high",
                    "summary_minimal": MarkdownParser.extract_summary_minimal(
                        mandate_content, mid
                    ),
                    "summary_runtime": MarkdownParser.extract_summary_runtime(
                        mandate_content, mid
                    ),
                }
                for mid in md_ids
            ]
        elif legacy_mandate.exists():
            mandate_content = legacy_mandate.read_text(encoding="utf-8")
            self.core_items = LegacySpecParser.parse_mandates(mandate_content)
        else:
            abs_path = (spec_root / "mandate.md").resolve()
            raise FileNotFoundError(
                f"mandate.spec not found at {abs_path}. "
                "Run 'sdd docs update' to generate docs-meta artifacts."
            )

        # Guidelines: prefer guidelines.md, fall back to guidelines.dsl
        md_guidelines = spec_root / "guidelines.md"
        legacy_guidelines = spec_root / "guidelines.dsl"

        if md_guidelines.exists():
            gl_content = md_guidelines.read_text(encoding="utf-8")
            gl_ids = re.findall(r"^#{1,3}\s+(G\d+)[:\s]", gl_content, re.MULTILINE)
            self.client_items = [
                {
                    "id": g_id,
                    "type": "GUIDELINE",
                    "title": MarkdownParser.extract_summary_minimal(gl_content, g_id)
                    or g_id,
                    "status": "active",
                    "criticality": "medium",
                    "summary_minimal": MarkdownParser.extract_summary_minimal(
                        gl_content, g_id
                    ),
                    "summary_runtime": MarkdownParser.extract_summary_runtime(
                        gl_content, g_id
                    ),
                }
                for g_id in gl_ids
            ]
        elif legacy_guidelines.exists():
            gl_content = legacy_guidelines.read_text(encoding="utf-8")
            # Legacy block format: `guideline G001 { ... }`
            block_items = LegacySpecParser.parse_guidelines_blocks(gl_content)
            if block_items:
                self.client_items = block_items
            else:
                # Compact key-value format: `G01: Title` (one entry per block)
                gl_matches = re.findall(
                    r"^\s*(G\d+)\s*:\s+(.+)$", gl_content, re.MULTILINE
                )
                if gl_matches:
                    compact_map = {
                        gid: title.strip() for gid, title in gl_matches if gid.strip()
                    }
                    self.client_items = [
                        {
                            "id": g_id,
                            "type": "GUIDELINE",
                            "title": compact_map[g_id] or g_id,
                            "status": "active",
                            "criticality": "medium",
                        }
                        for g_id in sorted(compact_map)
                    ]
                else:
                    # Bullet/label fallback: `- [G01] ...`
                    bullet_ids = sorted(set(re.findall(r"\[(G\d+)\]", gl_content)))
                    self.client_items = [
                        {
                            "id": g_id,
                            "type": "GUIDELINE",
                            "title": g_id,
                            "status": "active",
                            "criticality": "medium",
                        }
                        for g_id in bullet_ids
                    ]
        else:
            self.client_items = []

        # Phase 2: Deterministic Fingerprinting
        core_fingerprint = GovernanceFingerprinter.generate(self.core_items)
        # Client fingerprint uses core hash as salt to maintain referential integrity
        client_fingerprint = GovernanceFingerprinter.generate(
            self.client_items, salt=core_fingerprint
        )

        self.result = {
            self.CORE_KEY: {
                "fingerprint": core_fingerprint,
                "version": self.SCHEMA_VERSION,
            },
            self.CLIENT_KEY: {
                "fingerprint": client_fingerprint,
                "fingerprint_core_salt": core_fingerprint,
                "version": self.SCHEMA_VERSION,
            },
            "core_items": self.core_items,
            "client_items": self.client_items,
        }
        return self.result

    def save_outputs(self, output_dir: str) -> dict[str, Any]:
        """Saves the built JSON artifacts for Phase 2 (Compiler)."""
        if not self.result:
            self.build()

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        core_output = {
            "category": "CORE",
            "version": self.result["governance_core"]["version"],
            "fingerprint": self.result["governance_core"]["fingerprint"],
            "items": self.result["core_items"],
        }

        client_output = {
            "category": "CLIENT",
            "version": self.result["governance_client"]["version"],
            "fingerprint": self.result["governance_client"]["fingerprint"],
            "fingerprint_core_salt": self.result["governance_client"][
                "fingerprint_core_salt"
            ],
            "items": self.result["client_items"],
        }

        core_path = out_path / "governance-core.json"
        client_path = out_path / "governance-client.json"

        with open(core_path, "w", encoding="utf-8") as f:
            json.dump(core_output, f, indent=2, ensure_ascii=False)

        with open(client_path, "w", encoding="utf-8") as f:
            json.dump(client_output, f, indent=2, ensure_ascii=False)

        return {
            "governance_core": str(core_path),
            "governance_client": str(client_path),
            "core_fingerprint": core_output["fingerprint"],
            "client_fingerprint": client_output["fingerprint"],
        }
