#!/usr/bin/env python3
"""
Standalone test of DSL Compiler on real SDD v3.0 files
"""

import importlib
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
tests_dir = repo_root / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

_path_config = importlib.import_module("tests.path_config")
REPO_ROOT = _path_config.REPO_ROOT
SPEC_DIR = _path_config.SPEC_DIR

compile_file = importlib.import_module("sdd_compiler.dsl_compiler").compile_file


def main() -> int:
    workspace = REPO_ROOT

    files_to_compile = [
        (SPEC_DIR / "mandate.spec", "mandate.spec.compiled.json"),
        (SPEC_DIR / "guidelines.dsl", "guidelines.dsl.compiled.json"),
    ]

    print("=" * 70)
    print("DSL COMPILER - REAL DATA TEST")
    print("=" * 70)
    print()

    total_input = 0
    total_output = 0

    for input_path, output_filename in files_to_compile:
        output_path = workspace / output_filename

        if not input_path.exists():
            print(f"❌ File not found: {input_path}")
            continue

        print(f"Compiling: {input_path.name}")
        print(f"  Location: {input_path}")

        metrics = compile_file(str(input_path), str(output_path))

        if not metrics.success:
            print("  ❌ Compilation FAILED")
            for error in metrics.errors:
                print(f"     Error: {error}")
            print()
            continue

        print("  ✅ Success!")
        print(f"     Input Size:      {metrics.input_size:>10,} bytes")
        print(f"     Output Size:     {metrics.output_size:>10,} bytes")
        print(f"     Compression:     {metrics.compression_ratio:>10.1%}")
        print(f"     Mandates:        {metrics.mandates_compiled:>10}")
        print(f"     Guidelines:      {metrics.guidelines_compiled:>10}")
        print(f"     Unique Strings:  {metrics.unique_strings:>10}")
        print(f"     Compilation:     {metrics.compilation_time_ms:>10.2f} ms")
        print(f"     Output File:     {output_path.name}")
        print()

        total_input += metrics.input_size
        total_output += metrics.output_size

    if total_input > 0:
        total_compression = (total_input - total_output) / total_input

        print("=" * 70)
        print("COMBINED METRICS")
        print("=" * 70)
        print(f"Total Input:       {total_input:>10,} bytes")
        print(f"Total Output:      {total_output:>10,} bytes")
        print(f"Reduction:         {total_input - total_output:>10,} bytes")
        print(f"Compression:       {total_compression:>10.1%}")
        print()

        if total_compression >= 0.65:
            print("✅ SUCCESS: Compression ratio meets target (≥ 65%)")
            return 0
        elif total_compression >= 0.50:
            print(
                f"⚠️  WARNING: Compression ratio {total_compression:.1%} below target 65%"
            )
            print("   But still acceptable (>50%)")
            return 0
        else:
            print(f"❌ FAILED: Compression ratio {total_compression:.1%} < 50%")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
