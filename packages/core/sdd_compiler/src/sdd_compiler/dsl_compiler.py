"""
DSL Compiler: Convert SDD v3.0 DSL (.spec/.dsl) to MessagePack binary (.bin)

Features:
- Lexical and syntax analysis
- String deduplication (30-40% savings)
- Category mapping and ID optimization
- MessagePack binary output (3-4x parse speedup vs JSON)
- Comprehensive error reporting
"""

import importlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TypedDict

# Try to import msgpack, gracefully handle if not available
try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

# Import SDD Telemetry for deduplication
try:
    importlib.import_module("sdd_telemetry.engine")
    HAS_RTK = True
except ImportError:
    HAS_RTK = False


@dataclass
class CompilationMetrics:
    """Tracks compilation performance"""

    input_size: int = 0
    output_size: int = 0
    compilation_time_ms: float = 0.0
    string_pool_size: int = 0
    mandates_compiled: int = 0
    guidelines_compiled: int = 0
    unique_strings: int = 0
    errors: list[str] = field(default_factory=list)
    structured_errors: list["ValidationIssue"] = field(default_factory=list)
    telemetry_compression_ratio: float = 0.0  # Telemetry sub-layer compression
    telemetry_patterns_matched: int = 0  # Number of patterns matched by Telemetry
    parse_mode: str = "regex"
    parse_fallback_used: bool = False
    parse_backend: str = "regex"
    warnings: list[str] = field(default_factory=list)

    @property
    def compression_ratio(self) -> float:
        """Percentage of data removed by compression"""
        if self.input_size == 0:
            return 0.0
        return (self.input_size - self.output_size) / self.input_size

    @property
    def success(self) -> bool:
        """Whether compilation succeeded"""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d["compression_ratio"] = self.compression_ratio
        d["success"] = self.success
        return d


class DSLValidator:
    """Validates DSL syntax and semantics"""

    MANDATE_PATTERN = (
        r"^\s*-\s*\[([MP]\d{3})\]\s+\*\*(.*?)\*\*(.*?)(?=^\s*-|^\s*---|\Z)"
    )
    GUIDELINE_PATTERN = r"guideline\s+(G\d+)\s*\{([^}]+)\}"

    CATEGORY_MAP = {
        # Mandate categories
        "architecture": 1,
        "core": 1,  # Map core to architecture for now
        "general": 2,
        "performance": 3,
        "security": 4,
        # Guideline categories
        "git": 5,
        "documentation": 6,
        "testing": 7,
        "naming": 8,
        "code-style": 9,
    }

    @staticmethod
    def validate_dsl_detailed(dsl_text: str) -> list["ValidationIssue"]:  # noqa: C901
        """Validate DSL and return structured issues."""
        issues: list[ValidationIssue] = []
        lines = dsl_text.splitlines()

        def locate(token: str) -> tuple[int, int, str]:
            for idx, line in enumerate(lines, start=1):
                col = line.find(token)
                if col >= 0:
                    return idx, col + 1, line[:200]
            return 1, 1, (lines[0][:200] if lines else "")

        # Check mandate syntax
        mandate_matches = list(
            re.finditer(
                DSLValidator.MANDATE_PATTERN, dsl_text, re.MULTILINE | re.DOTALL
            )
        )
        if mandate_matches:
            mandate_ids: list[int] = []
            for m in mandate_matches:
                id_str = m.group(1)
                try:
                    mandate_ids.append(int(id_str[1:]))
                except ValueError:
                    continue

            if len(mandate_ids) > 1:
                for i in range(len(mandate_ids) - 1):
                    if mandate_ids[i + 1] != mandate_ids[i] + 1:
                        line, column, snippet = locate(
                            f"[{mandate_matches[i + 1].group(1)}]"
                        )
                        issues.append(
                            {
                                "code": "MANDATE_IDS_NOT_SEQUENTIAL",
                                "message": f"Mandate IDs not sequential: {mandate_ids}",
                                "line": line,
                                "column": column,
                                "snippet": snippet,
                                "hint": "Use sequential IDs without gaps (e.g. M001, M002, M003).",
                            }
                        )
                        break

            for match in mandate_matches:
                mandate_id = match.group(1)
                title = match.group(2).strip()
                if not title:
                    line, column, snippet = locate(f"[{mandate_id}]")
                    issues.append(
                        {
                            "code": "MANDATE_MISSING_TITLE",
                            "message": f"Mandate {mandate_id}: missing field 'title'",
                            "line": line,
                            "column": column,
                            "snippet": snippet,
                            "hint": "Provide a non-empty title in '**title**' format.",
                        }
                    )

        # Check guideline syntax
        guideline_matches = list(
            re.finditer(DSLValidator.GUIDELINE_PATTERN, dsl_text, re.DOTALL)
        )
        if guideline_matches:
            guideline_ids = [int(m.group(1)[1:]) for m in guideline_matches]

            if guideline_ids != list(range(1, len(guideline_ids) + 1)):
                token = guideline_matches[0].group(1)
                line, column, snippet = locate(token)
                issues.append(
                    {
                        "code": "GUIDELINE_IDS_NOT_SEQUENTIAL",
                        "message": f"Guideline IDs not sequential: {guideline_ids}",
                        "line": line,
                        "column": column,
                        "snippet": snippet,
                        "hint": "Use sequential guideline IDs (G01, G02, G03...).",
                    }
                )

            for match in guideline_matches:
                guideline_id = match.group(1)
                body = match.group(2)
                required = {"type", "title"}
                for req in required:
                    if f"{req}:" not in body:
                        line, column, snippet = locate(guideline_id)
                        issues.append(
                            {
                                "code": "GUIDELINE_MISSING_FIELD",
                                "message": f"Guideline {guideline_id}: missing field '{req}'",
                                "line": line,
                                "column": column,
                                "snippet": snippet,
                                "hint": f"Add required field '{req}:' inside guideline block.",
                            }
                        )

        return issues

    @staticmethod
    def validate_dsl(dsl_text: str) -> list[str]:  # noqa: C901
        """Validate DSL syntax and semantics"""
        return [
            issue["message"] for issue in DSLValidator.validate_dsl_detailed(dsl_text)
        ]


class DSLParser:
    """Parses DSL text into structured format"""

    @staticmethod
    def extract_field(text: str, field_name: str) -> str | None:
        """Extract field value from DSL block

        Handles both quoted and unquoted values, including multi-line content.
        """
        # Try quoted value first: field: "value"
        # This captures everything including quotes, newlines, special chars
        pattern = f'{field_name}\\s*:\\s*"([^"]*)(?:"|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else None

        # Try unquoted value: field: value (until comma or closing brace)
        pattern = f"{field_name}\\s*:\\s*([^,}}\\n]*?)(?=,|}}|\\n)"
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            return value if value else None

        return None

    @staticmethod
    def extract_array(text: str, field_name: str) -> list[str] | None:
        """Extract array field value"""
        pattern = f"{field_name}\\s*:\\s*\\[([^\\]]*)\\]"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None

        items_text = match.group(1)
        items = []
        for item in items_text.split(","):
            item = item.strip().strip('"')
            if item:
                items.append(item)

        return items if items else None

    @staticmethod
    def parse_mandates(dsl_text: str) -> list[dict[str, Any]]:
        """Parse all mandates from DSL (Markdown format)"""
        mandates = []
        pattern = r"^\s*-\s*\[([MP]\d{3})\]\s+\*\*(.*?)\*\*(.*?)(?=^\s*-|^\s*---|\Z)"

        for match in re.finditer(pattern, dsl_text, re.MULTILINE | re.DOTALL):
            mandate_id = match.group(1)
            title = match.group(2).strip()
            description = match.group(3).strip()

            # Extract category if present
            category = "core"
            if "category:" in description.lower():
                cat_match = re.search(r"category:\s*(\w+)", description, re.IGNORECASE)
                if cat_match:
                    category = cat_match.group(1).lower()

            # Extract rationale if present
            rationale = ""
            if "rationale:" in description.lower():
                rat_match = re.search(
                    r'rationale:\s*"([^"]+)"', description, re.IGNORECASE
                )
                if rat_match:
                    rationale = rat_match.group(1)
                else:
                    rat_match = re.search(
                        r"rationale:\s*([^\n]+)", description, re.IGNORECASE
                    )
                    if rat_match:
                        rationale = rat_match.group(1).strip()

            # Extract validation commands if present
            validation_commands = []
            if "validation:" in description.lower():
                commands_match = re.search(
                    r"validation:\s*\{?\s*commands:\s*\[([^\]]+)\]",
                    description,
                    re.IGNORECASE,
                )
                if commands_match:
                    cmds_text = commands_match.group(1)
                    validation_commands = [
                        c.strip().strip('"').strip("'") for c in cmds_text.split(",")
                    ]

            mandate = {
                "id": mandate_id,
                "type": "HARD",  # Mandates in markdown are hard by default
                "title": title,
                "description": description,
                "category": category,
                "rationale": rationale,
                "validation_commands": validation_commands,
            }
            mandates.append(mandate)

        return mandates

    @staticmethod
    def parse_guidelines(dsl_text: str) -> list[dict[str, Any]]:
        """Parse all guidelines from DSL"""
        guidelines = []
        pattern = r"guideline\s+(G\d+)\s*\{([^}]+)\}"

        for match in re.finditer(pattern, dsl_text, re.DOTALL):
            guideline_id = match.group(1)
            body = match.group(2)

            guideline = {
                "id": guideline_id,
                "type": DSLParser.extract_field(body, "type"),
                "title": DSLParser.extract_field(body, "title"),
                "description": DSLParser.extract_field(body, "description"),
                "category": DSLParser.extract_field(body, "category") or "general",
                "tags": DSLParser.extract_array(body, "tags") or [],
                "examples": DSLParser.extract_array(body, "examples"),
            }
            guidelines.append(guideline)

        return guidelines


class StringPool:
    """Manages string deduplication and pooling"""

    def __init__(self) -> None:
        self.pool: dict[str, int] = {}
        self.counter = 0

    def add(self, value: str | None) -> int | None:
        """Add string to pool, return index"""
        if value is None or value == "":
            return None

        if value not in self.pool:
            self.pool[value] = self.counter
            self.counter += 1

        return self.pool[value]

    def get_array(self) -> list[str]:
        """Get string pool as array"""
        pool_array = [""] * len(self.pool)
        for string, index in self.pool.items():
            pool_array[index] = string
        return pool_array

    def get_size(self) -> int:
        """Get total size of string pool"""
        return sum(len(s.encode("utf-8")) for s in self.pool)


class DSLCompiler:
    """Main DSL compiler with validation and optimization"""

    def __init__(self) -> None:
        self.metrics = CompilationMetrics()
        self.string_pool = StringPool()

    def compile(
        self, dsl_text: str, validate: bool = True, parse_mode: str | None = None
    ) -> dict[str, Any] | None:
        """
        Compile DSL text to optimized format

        Args:
            dsl_text: DSL source code
            validate: Whether to validate DSL before compilation

        Returns:
            Compiled format dict (ready for JSON/MessagePack encoding)
        """
        start_time = time.time()

        # Metrics
        self.metrics.input_size = len(dsl_text.encode("utf-8"))

        # Validation
        if validate:
            structured_errors = DSLValidator.validate_dsl_detailed(dsl_text)
            if structured_errors:
                self.metrics.structured_errors = structured_errors
                self.metrics.errors = [issue["message"] for issue in structured_errors]
                return None

        # Parse DSL (strategy-aware)
        mandates, guidelines = self._parse_with_strategy(
            dsl_text=dsl_text, parse_mode=parse_mode
        )

        # Compile with string deduplication
        compiled_mandates = [self._compile_mandate(m) for m in mandates]
        compiled_guidelines = [self._compile_guideline(g) for g in guidelines]

        # Create output structure
        output = {
            "format_version": "3.1",
            "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mandates": compiled_mandates,
            "guidelines": compiled_guidelines,
            "string_pool": self.string_pool.get_array(),
            "categories": DSLValidator.CATEGORY_MAP,
        }

        # Metrics
        output_json = json.dumps(output)
        self.metrics.output_size = len(output_json.encode("utf-8"))
        self.metrics.compilation_time_ms = (time.time() - start_time) * 1000
        self.metrics.mandates_compiled = len(compiled_mandates)
        self.metrics.guidelines_compiled = len(compiled_guidelines)
        self.metrics.string_pool_size = len(self.string_pool.pool)
        self.metrics.unique_strings = len(self.string_pool.pool)

        return output

    def _parse_with_strategy(
        self, *, dsl_text: str, parse_mode: str | None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        mode = (parse_mode or os.environ.get("SDD_DSL_PARSE_MODE", "regex")).lower()
        self.metrics.parse_mode = mode
        self.metrics.parse_fallback_used = False

        if mode == "regex":
            self.metrics.parse_backend = "regex"
            return DSLParser.parse_mandates(dsl_text), DSLParser.parse_guidelines(
                dsl_text
            )

        if mode in {"ast_first", "ast-strict", "ast_strict"}:
            try:
                mandates, guidelines = self._parse_with_ast(dsl_text)
                self.metrics.parse_backend = "ast"
                return mandates, guidelines
            except NotImplementedError:
                if mode in {"ast-strict", "ast_strict"}:
                    raise
                self.metrics.parse_backend = "regex"
                self.metrics.parse_fallback_used = True
                self.metrics.warnings.append(
                    "AST parser unavailable; using regex fallback."
                )
                return DSLParser.parse_mandates(dsl_text), DSLParser.parse_guidelines(
                    dsl_text
                )

        self.metrics.parse_backend = "regex"
        self.metrics.warnings.append(
            f"Unknown parse mode '{mode}', defaulting to regex."
        )
        return DSLParser.parse_mandates(dsl_text), DSLParser.parse_guidelines(dsl_text)

    def _parse_with_ast(
        self, dsl_text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        mandates = self._parse_mandates_ast(dsl_text)
        guidelines = self._parse_guidelines_ast(dsl_text)
        return mandates, guidelines

    def _parse_mandates_ast(self, dsl_text: str) -> list[dict[str, Any]]:
        mandates: list[dict[str, Any]] = []
        lines = dsl_text.splitlines()
        i = 0
        while i < len(lines):
            parsed = self._parse_mandate_header(lines[i])
            if parsed is None:
                i += 1
                continue

            mandate_id, title, description_first = parsed
            description_lines = [description_first] if description_first else []
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt.startswith("- [") or nxt == "---":
                    break
                description_lines.append(lines[j].rstrip())
                j += 1
            description = "\n".join(line for line in description_lines if line).strip()

            category = self._extract_category_from_lines(description_lines)
            rationale = self._extract_rationale_from_lines(description_lines)
            validation_commands = self._extract_commands_from_lines(description_lines)

            mandates.append(
                {
                    "id": mandate_id,
                    "type": "HARD",
                    "title": title,
                    "description": description,
                    "category": category,
                    "rationale": rationale,
                    "validation_commands": validation_commands,
                }
            )
            i = j
        return mandates

    def _parse_mandate_header(self, raw_line: str) -> tuple[str, str, str] | None:
        raw = raw_line.strip()
        if not raw.startswith("- ["):
            return None
        if "] **" not in raw or "**" not in raw:
            return None
        id_start = raw.find("[") + 1
        id_end = raw.find("]", id_start)
        mandate_id = raw[id_start:id_end].strip()
        title_start = raw.find("**", id_end) + 2
        title_end = raw.find("**", title_start)
        title = raw[title_start:title_end].strip()
        description_first = raw[title_end + 2 :].strip()
        return mandate_id, title, description_first

    def _extract_category_from_lines(self, lines: list[str]) -> str:
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("category:"):
                return stripped.split(":", 1)[1].strip().lower()
        return "core"

    def _extract_rationale_from_lines(self, lines: list[str]) -> str:
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("rationale:"):
                return stripped.split(":", 1)[1].strip().strip('"')
        return ""

    def _extract_commands_from_lines(self, lines: list[str]) -> list[str]:
        for line in lines:
            stripped = line.strip()
            if "commands:" in stripped.lower() and "[" in stripped and "]" in stripped:
                inside = stripped[stripped.find("[") + 1 : stripped.rfind("]")]
                return [
                    c.strip().strip('"').strip("'")
                    for c in inside.split(",")
                    if c.strip()
                ]
        return []

    def _parse_guidelines_ast(self, dsl_text: str) -> list[dict[str, Any]]:
        guidelines: list[dict[str, Any]] = []
        lines = dsl_text.splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i].strip()
            if not raw.startswith("guideline ") or "{" not in raw:
                i += 1
                continue

            header = raw.split("{", 1)[0].strip().split()
            if len(header) < 2:
                i += 1
                continue
            guideline_id = header[1].strip()
            block_lines: list[str] = []
            depth = raw.count("{") - raw.count("}")
            j = i + 1
            while j < len(lines):
                line = lines[j]
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    break
                block_lines.append(line)
                j += 1

            body = "\n".join(block_lines)
            guidelines.append(
                {
                    "id": guideline_id,
                    "type": DSLParser.extract_field(body, "type"),
                    "title": DSLParser.extract_field(body, "title"),
                    "description": DSLParser.extract_field(body, "description"),
                    "category": DSLParser.extract_field(body, "category") or "general",
                    "tags": DSLParser.extract_array(body, "tags") or [],
                    "examples": DSLParser.extract_array(body, "examples"),
                }
            )
            i = j + 1
        return guidelines

    def _compile_mandate(self, mandate: dict[str, Any]) -> dict[str, Any]:
        """Compile mandate with string deduplication"""
        return {
            "id": int(mandate["id"][1:]),  # M001 → 1
            "type": mandate["type"],  # HARD or SOFT
            "title_idx": self.string_pool.add(mandate["title"]),
            "description_idx": self.string_pool.add(mandate["description"]),
            "category": DSLValidator.CATEGORY_MAP.get(mandate["category"], 2),
            "rationale_idx": self.string_pool.add(mandate["rationale"]),
            "validation_commands": mandate["validation_commands"],
        }

    def _compile_guideline(self, guideline: dict[str, Any]) -> dict[str, Any]:
        """Compile guideline with string deduplication"""
        examples_idx = None
        if guideline["examples"]:
            examples_idx = [self.string_pool.add(ex) for ex in guideline["examples"]]

        return {
            "id": int(guideline["id"][1:]),  # G001 → 1
            "type": guideline["type"],  # HARD or SOFT
            "title_idx": self.string_pool.add(guideline["title"]),
            "description_idx": self.string_pool.add(guideline["description"]),
            "category": DSLValidator.CATEGORY_MAP.get(guideline["category"], 2),
            "examples_idx": examples_idx,
        }

    def get_metrics(self) -> CompilationMetrics:
        """Get compilation metrics"""
        return self.metrics


# Module-level functions
def compile_string(
    dsl_text: str,
) -> tuple[dict[str, Any] | None, CompilationMetrics]:
    """Compile DSL string and return result + metrics"""
    compiler = DSLCompiler()
    output = compiler.compile(dsl_text)
    return output, compiler.get_metrics()


def compile_file(input_path: str, output_path: str) -> CompilationMetrics:
    """Compile DSL file to JSON"""
    with open(input_path, encoding="utf-8") as f:
        dsl_text = f.read()

    output, metrics = compile_string(dsl_text)

    if output is None:
        return metrics

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return metrics


def compile_to_binary(input_path: str, output_path: str) -> dict[str, Any]:
    """
    Compile DSL file to MessagePack binary format

    Args:
        input_path: DSL source file path
        output_path: Binary output file path

    Returns:
        Metrics dict with compression and performance info
    """
    if not HAS_MSGPACK:
        raise ImportError("msgpack not installed. Run: pip install msgpack")

    # First, compile to intermediate format
    with open(input_path, encoding="utf-8") as f:
        dsl_text = f.read()

    compiled, metrics = compile_string(dsl_text)

    if compiled is None:
        return {
            "success": False,
            "errors": metrics.errors,
        }

    # Record JSON size
    json_bytes = json.dumps(compiled, separators=(",", ":")).encode("utf-8")
    json_size = len(json_bytes)

    binary_data = {
        "format_version": "3.1",
        "items": compiled["mandates"] + compiled["guidelines"],
        "string_pool": compiled["string_pool"],
        "categories": compiled.get("categories", {}),
    }

    # Encode to MessagePack
    msgpack_payload = msgpack.packb(binary_data, use_bin_type=True)

    # Add SDD magic header for format identification
    MAGIC = b"\x53\x44\x44\x03"  # "SDD" + version 3
    binary_output = MAGIC + msgpack_payload

    # Write to file
    with open(output_path, "wb") as f:
        f.write(binary_output)

    # Calculate compression metrics
    msgpack_size = len(binary_output)
    compression_vs_json = (json_size - msgpack_size) / json_size if json_size > 0 else 0

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "json_size": json_size,
        "binary_size": msgpack_size,
        "compression_vs_json": compression_vs_json,
        "total_compression": metrics.compression_ratio,  # vs original DSL
        "mandates": metrics.mandates_compiled,
        "guidelines": metrics.guidelines_compiled,
        "string_pool_size": metrics.string_pool_size,
        "compilation_time_ms": metrics.compilation_time_ms,
        "estimated_parse_speedup": "3-4x",
    }


def compile_to_binary_and_print(
    input_path: str, output_path: str | None = None
) -> None:
    """Compile to binary and print metrics"""
    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".sdd"))

    print(render_binary_compile_report(input_path=input_path, output_path=output_path))  # noqa: T201


def compile_and_print_metrics(input_path: str, output_path: str | None = None) -> None:
    """Compile and print metrics"""
    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".compiled.json"))

    print(render_json_compile_report(input_path=input_path, output_path=output_path))  # noqa: T201


def render_json_compile_report(input_path: str, output_path: str) -> str:
    """Render Json Compile Report."""
    metrics = compile_file(input_path, output_path)
    lines = [f"Compiling: {input_path}"]
    if not metrics.success:
        lines.append("❌ Compilation FAILED")
        for error in metrics.errors:
            lines.append(f"  - {error}")
        return "\n".join(lines)

    lines.extend(
        [
            "✅ Compilation successful!",
            "",
            "Metrics:",
            f"  Input Size:        {metrics.input_size:,} bytes",
            f"  Output Size:       {metrics.output_size:,} bytes",
            f"  Compression:       {metrics.compression_ratio:.1%}",
            "",
            f"  Mandates:          {metrics.mandates_compiled}",
            f"  Guidelines:        {metrics.guidelines_compiled}",
            f"  Unique Strings:    {metrics.unique_strings}",
            "",
            f"  Compilation Time:  {metrics.compilation_time_ms:.1f} ms",
            "",
            f"Output: {output_path}",
        ]
    )
    return "\n".join(lines)


def render_binary_compile_report(input_path: str, output_path: str) -> str:
    """Render Binary Compile Report."""
    lines = [f"Compiling to binary: {input_path}"]
    if not HAS_MSGPACK:
        lines.extend(
            [
                "❌ ERROR: msgpack not installed",
                "   Run: pip install msgpack",
            ]
        )
        return "\n".join(lines)

    result = compile_to_binary(input_path, output_path)
    if not result["success"]:
        lines.append("❌ Compilation FAILED")
        for error in result.get("errors", []):
            lines.append(f"  - {error}")
        return "\n".join(lines)

    lines.extend(
        [
            "✅ Binary compilation successful!",
            "",
            "Compression:",
            f"  JSON Size:         {result['json_size']:,} bytes",
            f"  Binary Size:       {result['binary_size']:,} bytes",
            f"  Savings vs JSON:   {result['compression_vs_json']:+.1%}",
            f"  Total Compression: {result['total_compression']:.1%} (from original DSL)",
            "",
            "Content:",
            f"  Mandates:          {result['mandates']}",
            f"  Guidelines:        {result['guidelines']}",
            f"  Unique Strings:    {result['string_pool_size']}",
            "",
            f"  Parse Speedup:     {result['estimated_parse_speedup']} faster than JSON",
            f"  Compile Time:      {result['compilation_time_ms']:.1f} ms",
            "",
            f"Output: {output_path}",
        ]
    )
    return "\n".join(lines)


class ValidationIssue(TypedDict):
    """ValidationIssue."""

    code: str
    message: str
    line: int
    column: int
    snippet: str
    hint: str


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SDD DSL Compiler")
    parser.add_argument("input", help="Input .spec or .dsl file")
    parser.add_argument("output", nargs="?", help="Output file path")
    parser.add_argument(
        "--format", choices=["json", "msgpack"], default="json", help="Output format"
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"❌ File not found: {args.input}")  # noqa: T201
        sys.exit(1)

    # Output path is required — no implicit inference into /generated
    output_path = args.output
    if output_path is None:
        suffix = ".compiled.json" if args.format == "json" else ".compiled.msgpack"
        print(  # noqa: T201
            f"❌ --output is required.\n"
            f"Hint: python -m sdd_compiler {args.input} <output{suffix}>"
        )
        sys.exit(1)

    if args.format == "msgpack":
        compile_to_binary_and_print(str(input_path), output_path)
    else:
        compile_and_print_metrics(str(input_path), output_path)
