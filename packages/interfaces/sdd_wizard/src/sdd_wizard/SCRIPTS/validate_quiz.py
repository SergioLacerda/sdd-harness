#!/usr/bin/env python3
"""
VALIDATION QUIZ EXECUTOR
Runs ia-rules.md comprehension quiz interactively.

Usage:
    python docs/ia/scripts/validate_quiz.py

For AI Agents:
    Run this at start of FIRST_SESSION_SETUP to verify understanding.
"""

import importlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure packages is in path for tests.path_config
root = Path(__file__).resolve().parents[3]
if str(root / "packages") not in sys.path:
    sys.path.insert(0, str(root / "packages"))

QUIZ_TRACKING = importlib.import_module("tests.path_config").QUIZ_TRACKING


class ValidationQuiz:
    """Interactive quiz validator for ia-rules.md"""

    QUESTIONS = [
        {
            "id": 1,
            "question": "What is the source of truth priority when documents conflict?",
            "options": {
                "A": "ia-rules.md — because it has the most rules",
                "B": "constitution.md — because it's most stable",
                "C": "execution_state.md — because it's most recent",
                "D": "Whichever file you trust most",
            },
            "correct": "B",
            "explanation": "constitution.md is immutable and takes precedence. Rules prevent execution conflicts.",
            "reference": "ia-rules.md: Source of Truth Priority",
        },
        {
            "id": 2,
            "question": "You're working on a bug in Thread A. Can you modify code in Thread B if it helps fix Thread A?",
            "options": {
                "A": "Yes, good engineering is being flexible",
                "B": "No, thread isolation is mandatory",
                "C": "Only if you update execution_state.md",
                "D": "Only if Thread B is inactive",
            },
            "correct": "B",
            "explanation": "Thread isolation is MANDATORY (ADR-005). Each thread works in isolation to prevent conflicts.",
            "reference": "ADR-005-thread-isolation-mandatory.md",
        },
        {
            "id": 3,
            "question": "After implementing a feature, what MUST you do?",
            "options": {
                "A": "Just commit the code, documentation updates are optional",
                "B": "Update execution_state.md with decisions, questions, risks, and status",
                "C": "Run the test suite",
                "D": "Notify the team via Slack",
            },
            "correct": "B",
            "explanation": "Checkpointing is mandatory (ia-rules #14). Keep executable + documentation in sync.",
            "reference": "ia-rules.md: Checkpointing Protocol",
        },
        {
            "id": 4,
            "question": "Your code needs storage. Can you import 'storage/adapters/json_adapter.py' directly?",
            "options": {
                "A": "Yes, it's already implemented",
                "B": "No, always go through the Storage Port interface",
                "C": "Only if the adapter is marked public",
                "D": "Only if you document why",
            },
            "correct": "B",
            "explanation": "Never bypass ports (ia-rules #1). Ports are abstraction layers preventing fragility.",
            "reference": "ADR-003-ports-adapters-pattern.md",
        },
        {
            "id": 5,
            "question": "You notice known_issues.md disagrees with your observation. What do you do?",
            "options": {
                "A": "Update known_issues.md immediately",
                "B": "Ignore it and implement your solution",
                "C": "Document your finding in execution_state.md, then update known_issues.md",
                "D": "Trust the documentation, don't question it",
            },
            "correct": "C",
            "explanation": "Document gaps (ia-rules #16): Reality ≠ docs is normal. Include evidence, update tracking.",
            "reference": "ia-rules.md: Gap Documentation",
        },
    ]

    PASSING_SCORE = 4  # 80% (4 out of 5)
    PASSING_PERCENTAGE = 80

    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.answers: dict[int, str] = {}
        self.score = 0

    def run_quiz(self) -> bool:
        """Run interactive quiz. Returns True if passed."""
        print("\n" + "=" * 70)  # noqa: T201
        print("📋 VALIDATION QUIZ — ia-rules.md Comprehension Check")  # noqa: T201
        print("=" * 70)  # noqa: T201
        print(f"\nSession ID: {self.session_id}")  # noqa: T201
        print(  # noqa: T201
            f"Passing Score: {self.PASSING_SCORE}/{len(self.QUESTIONS)} ({self.PASSING_PERCENTAGE}%)"
        )
        print("Instructions: Answer each question with A/B/C/D\n")  # noqa: T201

        # Ask each question
        for q in self.QUESTIONS:
            self._ask_question(q)

        # Calculate results
        return self._show_results()

    def _ask_question(self, q: dict[str, Any]) -> None:
        """Ask a single question and record answer."""
        print(f"\n--- Question {q['id']}/{len(self.QUESTIONS)} ---")  # noqa: T201
        print(f"{q['question']}\n")  # noqa: T201

        # Show options
        for opt_key, opt_text in q["options"].items():
            print(f"  {opt_key}) {opt_text}")  # noqa: T201

        # Get answer
        while True:
            answer = input("\nYour answer (A/B/C/D): ").strip().upper()
            if answer in ["A", "B", "C", "D"]:
                break
            print("❌ Invalid. Please enter A, B, C, or D")  # noqa: T201

        self.answers[q["id"]] = answer

        # Immediate feedback
        is_correct = answer == q["correct"]
        self.score += 1 if is_correct else 0

        if is_correct:
            print("✅ Correct!")  # noqa: T201
        else:
            print(f"❌ Incorrect. The correct answer is {q['correct']}")  # noqa: T201

        print(f"\n📚 {q['explanation']}")  # noqa: T201
        print(f"📖 Reference: {q['reference']}")  # noqa: T201

    def _show_results(self) -> bool:
        """Display results and determine pass/fail."""
        end_time = datetime.now()
        duration_minutes = (end_time - self.start_time).total_seconds() / 60
        percentage = (self.score / len(self.QUESTIONS)) * 100
        passed = self.score >= self.PASSING_SCORE

        print("\n" + "=" * 70)  # noqa: T201
        print("📊 QUIZ RESULTS")  # noqa: T201
        print("=" * 70)  # noqa: T201
        print(f"\nScore: {self.score}/{len(self.QUESTIONS)} ({percentage:.0f}%)")  # noqa: T201
        print(f"Duration: {duration_minutes:.1f} minutes")  # noqa: T201
        print(f"Status: {'✅ PASSED' if passed else '❌ FAILED'}")  # noqa: T201

        if not passed:
            print(  # noqa: T201
                f"\n⚠️  You need {self.PASSING_SCORE - self.score} more correct to pass."
            )
            print("\n📖 Next Steps:")  # noqa: T201
            print("  1. Re-read ia-rules.md (full document, ~10 min)")  # noqa: T201
            print("  2. Wait 30 minutes (memory consolidation)")  # noqa: T201
            print("  3. Retry this quiz")  # noqa: T201
            print("  4. After passing: continue with FIRST_SESSION_SETUP.md")  # noqa: T201
        else:
            print("\n✅ Excellent! You understand the core protocols.")  # noqa: T201
            print("\n🚀 Next Steps:")  # noqa: T201
            print("  1. Continue with FIRST_SESSION_SETUP.md (minute 9+)")  # noqa: T201
            print("  2. Read guides/QUICK_START.md to choose your PATH")  # noqa: T201
            print("  3. Proceed to work")  # noqa: T201

        # Log result
        self._log_attempt(passed, percentage, duration_minutes)

        return passed

    def _log_attempt(self, passed: bool, percentage: float, duration: float) -> None:
        """Log quiz attempt to tracking file."""
        tracking_file = QUIZ_TRACKING

        correct_q = [
            q_id
            for q_id, ans in self.answers.items()
            if ans == self.QUESTIONS[q_id - 1]["correct"]
        ]
        incorrect_q = [
            q_id
            for q_id, ans in self.answers.items()
            if ans != self.QUESTIONS[q_id - 1]["correct"]
        ]

        record = {
            "session_id": self.session_id,
            "timestamp": self.start_time.isoformat() + "Z",
            "agent_type": "human-or-claude",
            "score": self.score,
            "total": len(self.QUESTIONS),
            "percentage": percentage,
            "passed": passed,
            "attempt_number": self._get_attempt_number(),
            "time_minutes": round(duration, 1),
            "questions_correct": correct_q,
            "questions_incorrect": incorrect_q,
        }

        # Append to file (JSON Lines format)
        try:
            if tracking_file.exists():
                with open(tracking_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            else:
                with open(tracking_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            print(f"\n📊 Result logged to: {tracking_file}")  # noqa: T201
        except Exception as e:
            print(f"\n⚠️  Could not log result: {e}")  # noqa: T201

    def _get_attempt_number(self) -> int:
        """Get attempt number by counting previous sessions."""
        tracking_file = QUIZ_TRACKING

        if not tracking_file.exists():
            return 1

        try:
            with open(tracking_file, encoding="utf-8") as f:
                lines = f.readlines()
                attempts = sum(
                    1
                    for line in lines
                    if json.loads(line).get("session_id") == self.session_id
                )
            return attempts + 1
        except Exception:
            return 1


def main() -> int:
    """Entry point."""
    quiz = ValidationQuiz()
    passed = quiz.run_quiz()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
