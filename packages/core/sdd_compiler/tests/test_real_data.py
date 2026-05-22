#!/usr/bin/env python3
"""
Quick test of DSL Compiler against real SDD v3.0 files

Tests:
1. Compile mandate.spec
2. Compile guidelines.dsl
3. Verify metrics and compression ratios
"""

from pathlib import Path

from sdd_compiler.dsl_compiler import compile_file


def test_real_files() -> None:
    """Test compilation on real SDD v3.0 files"""

    files_to_compile = [
        ("../../spec/mandate.spec", "mandate.spec.compiled.json"),
        ("../../spec/guidelines.dsl", "guidelines.dsl.compiled.json"),
    ]

    print("=" * 70)
    print("DSL COMPILER - REAL DATA TEST")
    print("=" * 70)
    print()

    total_input = 0
    total_output = 0

    for input_file, output_file in files_to_compile:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            print(f"❌ File not found: {input_file}")
            continue

        print(f"Compiling: {input_file}")
        metrics = compile_file(str(input_path), str(output_path))

        if not metrics.success:
            print("  ❌ Compilation FAILED")
            for error in metrics.errors:
                print(f"     - {error}")
            continue

        print("  ✅ Success!")
        print(f"     Input:       {metrics.input_size:>10,} bytes")
        print(f"     Output:      {metrics.output_size:>10,} bytes")
        print(f"     Compression: {metrics.compression_ratio:>10.1%}")
        print()

        total_input += metrics.input_size
        total_output += metrics.output_size

    if total_input > 0:
        total_compression = (total_input - total_output) / total_input

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total Input:       {total_input:>10,} bytes")
        print(f"Total Output:      {total_output:>10,} bytes")
        print(f"Total Compression: {total_compression:>10.1%}")
        print()

        if total_compression >= 0.65:
            print("✅ PASSED: Compression ratio ≥ 65%")
        else:
            print(f"⚠️  WARNING: Compression ratio {total_compression:.1%} < target 65%")


if __name__ == "__main__":
    test_real_files()
