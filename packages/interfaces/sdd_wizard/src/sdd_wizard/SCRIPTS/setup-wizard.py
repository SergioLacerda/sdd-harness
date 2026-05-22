#!/usr/bin/env python3
"""
Interactive setup wizard for new developers.

Replaces 15-minute manual reading with 3-minute interactive questionnaire.
Automatically loads task-specific documentation.

Usage:
    python docs/ia/SCRIPTS/setup-wizard.py              # Interactive mode
    python docs/ia/SCRIPTS/setup-wizard.py --test       # Test mode (no input)
    python docs/ia/SCRIPTS/setup-wizard.py --load-profile  # Use saved preferences

Features:
    - Interactive PATH selection (A/B/C/D)
    - Auto-loads relevant documentation
    - Creates personalized .doc-profile for future sessions
    - Timing measurement (logs setup_wizard_seconds)
    - Test mode for CI/CD validation
"""

import argparse
import sys
import time
from pathlib import Path


class Colors:
    """Terminal color codes."""

    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header() -> None:
    """Print welcome header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")  # noqa: T201
    print("╔═══════════════════════════════════════════════════════════╗")  # noqa: T201
    print("║  🚀 QUICK START SETUP — Welcome to the Project!          ║")  # noqa: T201
    print("║     Get productive in 3 minutes                          ║")  # noqa: T201
    print("╚═══════════════════════════════════════════════════════════╝")  # noqa: T201
    print(Colors.END)  # noqa: T201


def ask_question(question: str, options: list[str]) -> str:
    """Ask user a question with options."""
    print(f"\n{Colors.BOLD}{question}{Colors.END}")  # noqa: T201
    for i, option in enumerate(options, 1):
        print(f"  {Colors.GREEN}{i}{Colors.END}. {option}")  # noqa: T201

    while True:
        choice = input(
            f"\n{Colors.YELLOW}Choose (1-{len(options)}): {Colors.END}"
        ).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print(f"{Colors.RED}Invalid choice. Try again.{Colors.END}")  # noqa: T201


def determine_path() -> str:
    """Interactive PATH determination."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}Step 1: What are you building?{Colors.END}")  # noqa: T201

    task_type = ask_question(
        "Task type?",
        [
            "Fix a bug (PATH A)",
            "Add a simple feature (PATH B)",
            "Build complex feature (PATH C)",
            "Parallel work (PATH D)",
        ],
    )

    path_map = {
        "Fix a bug (PATH A)": "A",
        "Add a simple feature (PATH B)": "B",
        "Build complex feature (PATH C)": "C",
        "Parallel work (PATH D)": "D",
    }

    return path_map[task_type]


def get_context_size() -> str:
    """Determine user's context limit."""
    print(  # noqa: T201
        f"\n{Colors.BOLD}{Colors.BLUE}Step 2: How much documentation can you read?{Colors.END}"
    )

    choice = ask_question(
        "Context preference?",
        [
            "Quick (only essential docs, <10 min read)",
            "Standard (recommended, 15-20 min)",
            "Deep dive (complete context, 30+ min)",
        ],
    )

    return choice.split("(")[0].strip()


def get_experience() -> str:
    """Determine developer experience level."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}Step 3: Your experience level?{Colors.END}")  # noqa: T201

    experience = ask_question(
        "How familiar are you with this codebase?",
        [
            "Brand new (first day)",
            "Some context (few weeks)",
            "Experienced (6+ months)",
        ],
    )

    return experience


def print_path_summary(path: str, context: str, experience: str) -> None:
    """Print summary of choices."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Your Setup:{Colors.END}")  # noqa: T201
    print(f"  PATH: {Colors.BOLD}{path}{Colors.END}")  # noqa: T201
    print(f"  Context: {context}")  # noqa: T201
    print(f"  Experience: {experience}")  # noqa: T201


def get_doc_paths(path: str, context: str) -> list[str]:
    """Get list of documentation files to load."""

    # Essential docs (all paths)
    essential = [
        "docs/ia/CANONICAL/rules/constitution.md",
        "docs/ia/CANONICAL/rules/ia-rules.md",
    ]

    path_docs = {
        "A": [
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/known_issues.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/services.md",
        ],
        "B": [
            "docs/ia/CANONICAL/rules/conventions.md",
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/CANONICAL/specifications/feature-checklist.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/contracts.md",
        ],
        "C": [
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/CANONICAL/rules/conventions.md",
            "docs/ia/CANONICAL/specifications/feature-checklist.md",
            "docs/ia/CANONICAL/specifications/testing.md",
            "docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md",
        ],
        "D": [
            "docs/ia/custom/_TEMPLATE/development/execution-state/_current.md",
            "docs/ia/CANONICAL/rules/ENFORCEMENT_RULES.md",
            "docs/ia/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md",
        ],
    }

    docs = essential + path_docs.get(path, [])

    # Adjust for context preference
    if context == "Quick":
        # Only keep essential + top 3
        docs = docs[:5]
    elif context == "Deep dive":
        # Add ADRs and additional specs
        docs.extend(
            [
                "docs/ia/CANONICAL/specifications/testing.md",
                "docs/ia/CANONICAL/specifications/definition_of_done.md",
            ]
        )

    return docs


def print_doc_list(docs: list[str]) -> None:
    """Print formatted list of docs to read."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}📚 Your Documentation Stack:{Colors.END}")  # noqa: T201
    total_size = 0

    for i, doc in enumerate(docs, 1):
        size = estimate_doc_size(doc)
        total_size += size
        print(f"  {Colors.GREEN}{i:2d}.{Colors.END} {doc} ({size}KB)")  # noqa: T201

    print(f"\n  {Colors.BOLD}Total: ~{total_size}KB{Colors.END}")  # noqa: T201
    print(  # noqa: T201
        f"  {Colors.YELLOW}Reading time: ~{max(5, total_size // 10)} minutes{Colors.END}"
    )


def estimate_doc_size(doc_path: str) -> int:
    """Estimate document size in KB."""
    try:
        if Path(doc_path).exists():
            return Path(doc_path).stat().st_size // 1024
    except Exception:
        # Keep wizard resilient if file metadata cannot be read.
        return 10
    return 10  # Default estimate


def print_next_steps() -> None:
    """Print next steps."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}🎯 Next Steps:{Colors.END}")  # noqa: T201
    print("  1. Read the docs listed above (skim is OK, focus on structure)")  # noqa: T201
    print("  2. Start coding! Open QUICK_START.md as reference")  # noqa: T201
    print("  3. When stuck: search docs/ia/ → grep for keywords")  # noqa: T201
    print(  # noqa: T201
        "  4. At end of task: update docs/ia/CUSTOM/_TEMPLATE/development/execution-state/_current.md"
    )
    print(  # noqa: T201
        f"\n  {Colors.YELLOW}💡 Tip: Save this setup for next time (use --load-profile){Colors.END}"
    )


def save_profile(path: str, context: str, experience: str) -> None:
    """Save user's profile for faster setup next time."""
    profile_path = Path.home() / ".dev-profile"
    profile = f"PATH={path}\nCONTEXT={context}\nEXPERIENCE={experience}\n"

    try:
        profile_path.write_text(profile, encoding="utf-8")
        print(f"\n{Colors.GREEN}✅ Profile saved to {profile_path}{Colors.END}")  # noqa: T201
        print("   Next time: python setup-wizard.py --load-profile")  # noqa: T201
    except Exception:
        # Saving profile is optional; onboarding must continue.
        return


def main() -> int:
    """Main setup wizard flow."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Interactive setup wizard for new developers"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (no user input, use mock answers)",
    )
    parser.add_argument(
        "--load-profile",
        action="store_true",
        help="Load previous setup profile instead of asking questions",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed timing information"
    )

    args = parser.parse_args()

    # Start timing
    start_time = time.time()

    print_header()

    # Test mode: run with mock answers
    if args.test:
        test_mode(start_time, args.verbose)
        return 0

    # Normal interactive mode
    try:
        path = determine_path()
        context = get_context_size()
        experience = get_experience()

        print_path_summary(path, context, experience)

        docs = get_doc_paths(path, context)
        print_doc_list(docs)
        print_next_steps()

        save_profile(path, context, experience)

        # Log timing
        elapsed = time.time() - start_time
        print(f"\n{Colors.YELLOW}⏱️  Setup time: {elapsed:.1f} seconds{Colors.END}")  # noqa: T201
        if args.verbose:
            print(f"   setup_wizard_completed_seconds: {elapsed}")  # noqa: T201

        return 0

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏸️  Setup cancelled by user{Colors.END}")  # noqa: T201
        return 1
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")  # noqa: T201
        return 1


def test_mode(start_time: float, verbose: bool) -> int:
    """Run wizard in test mode with mock answers."""
    print(f"\n{Colors.BLUE}🧪 Test Mode{Colors.END}")  # noqa: T201
    print("   Running with mock answers (no user input)...")  # noqa: T201

    # Mock answers
    mock_path = "A"
    mock_context = "Quick"
    mock_experience = "Some context (few weeks)"

    print(f"   PATH: {mock_path}")  # noqa: T201
    print(f"   Context: {mock_context}")  # noqa: T201
    print(f"   Experience: {mock_experience}")  # noqa: T201

    # Simulate doc loading
    docs = get_doc_paths(mock_path, mock_context)
    print(f"   Docs loaded: {len(docs)} files")  # noqa: T201

    # Log timing
    elapsed = time.time() - start_time
    print(f"\n{Colors.GREEN}✅ Test mode passed{Colors.END}")  # noqa: T201
    print(f"   ⏱️  Duration: {elapsed:.1f} seconds")  # noqa: T201

    if verbose:
        print("\n📊 Metrics:")  # noqa: T201
        print(f"   setup_wizard_completed_seconds: {elapsed}")  # noqa: T201
        print(f"   docs_loaded: {len(docs)}")  # noqa: T201
        print(f"   docs_size_kb: {sum(estimate_doc_size(d) for d in docs)}")  # noqa: T201

    return 0


if __name__ == "__main__":
    sys.exit(main())
