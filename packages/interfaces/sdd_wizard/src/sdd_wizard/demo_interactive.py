#!/usr/bin/env python3
"""
Demonstration of interactive wizard - shows a full walkthrough
with automated inputs for testing/demonstration purposes
"""

from pathlib import Path

from sdd_core.utils.process import SafeProcessRunner


def run_interactive_demo() -> None:
    """Run interactive wizard with automated inputs"""

    # Prepare inputs for the wizard
    # These are the responses to the interactive prompts
    inputs = [
        "",  # Press ENTER to continue (Step intro)
        "y",  # Preview mandate.spec? y
        "y",  # Preview guidelines.dsl? y
        "1",  # Select language: 1 (python)
        "y",  # Include M001? y
        "y",  # Include M002? y
        "",  # Project output directory (use default)
    ]

    # Join inputs with newlines and encode to bytes
    input_text = "\n".join(inputs)

    print("=" * 70)  # noqa: T201
    print("🧙 SDD WIZARD - INTERACTIVE MODE DEMONSTRATION")  # noqa: T201
    print("=" * 70)  # noqa: T201
    print()  # noqa: T201
    print("This script runs the wizard in INTERACTIVE mode with automated inputs.")  # noqa: T201
    print("Watch how the wizard guides you through project generation!")  # noqa: T201
    print()  # noqa: T201

    # Run the wizard
    cmd = ["./wizard.sh"]
    try:
        runner = SafeProcessRunner()
        cwd = Path(__file__).parent.parent.parent  # sdd-harness root
        result = runner.run_interactive(
            cmd,
            cwd=cwd,
            stdin_text=input_text,
            timeout=120,
        )

        if result.returncode == 0:
            print()  # noqa: T201
            print("=" * 70)  # noqa: T201
            print("✅ WIZARD COMPLETED SUCCESSFULLY!")  # noqa: T201
            print("=" * 70)  # noqa: T201
        else:
            print()  # noqa: T201
            print("=" * 70)  # noqa: T201
            print(f"❌ Wizard exited with code: {result.returncode}")  # noqa: T201
            print("=" * 70)  # noqa: T201

    except ValueError as e:
        print(f"❌ Security validation error: {e}")  # noqa: T201
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")  # noqa: T201
    except Exception as e:
        print(f"❌ Error: {e}")  # noqa: T201


if __name__ == "__main__":
    run_interactive_demo()
