#!/usr/bin/env python3
"""Draft generator for the ADR-021 enforcement-ladder threshold sign-off (A9).

`docs/adr/ADR-021-threshold-signoff.md` must mirror
`tools/ci/config/enforcement_ladder_thresholds.json` exactly, or
`check_enforcement_threshold_signoff.py` fails CI. Today that sync is done by
hand — this script drafts the numeric fields from the current thresholds
config, so a human only has to review the diff and fill in the approval
fields, instead of transcribing nine numbers.

It deliberately never fills in `Approved`/`Decision-Owner`/`Decision-Date`
with a real approval: those three fields are the human authorization gate
that `check_enforcement_threshold_signoff.py` exists to protect. If the
thresholds changed since the last sign-off, the draft resets those fields to
placeholders — the whole point is that a threshold change invalidates the
prior approval and must be re-signed by a human, not auto-carried-forward.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_PLACEHOLDER_APPROVED = "TBD"
_PLACEHOLDER_OWNER = "TBD"
_PLACEHOLDER_DATE = "TBD"

_HEADER_KEYS = ("approved", "decision-owner", "decision-date")


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _expected_pairs(cfg: dict[str, Any]) -> dict[str, str]:
    p = cfg.get("promotion_candidate", {})
    r = cfg.get("rollback_trigger", {})
    return {
        "window-days": str(int(cfg.get("window_days", 7))),
        "promotion-min-samples": str(int(p.get("min_samples", 0))),
        "promotion-max-false-block-rate": str(_as_float(p.get("max_false_block_rate"))),
        "promotion-max-rollback-rate": str(_as_float(p.get("max_rollback_rate"))),
        "promotion-max-rework-delta": str(_as_float(p.get("max_rework_delta"))),
        "rollback-min-samples": str(int(r.get("min_samples", 0))),
        "rollback-false-block-rate": str(_as_float(r.get("false_block_rate"))),
        "rollback-rate": str(_as_float(r.get("rollback_rate"))),
        "rollback-rework-delta": str(_as_float(r.get("rework_delta"))),
    }


def _parse_kv(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip()
    return data


def _numerically_equal(a: str, b: str) -> bool:
    try:
        return float(a) == float(b)
    except ValueError:
        return a == b


def _thresholds_unchanged(existing: dict[str, str], expected: dict[str, str]) -> bool:
    return all(
        _numerically_equal(existing.get(key, ""), value)
        for key, value in expected.items()
    )


_LABELS = {
    "window-days": "Window-Days",
    "promotion-min-samples": "Promotion-Min-Samples",
    "promotion-max-false-block-rate": "Promotion-Max-False-Block-Rate",
    "promotion-max-rollback-rate": "Promotion-Max-Rollback-Rate",
    "promotion-max-rework-delta": "Promotion-Max-Rework-Delta",
    "rollback-min-samples": "Rollback-Min-Samples",
    "rollback-false-block-rate": "Rollback-False-Block-Rate",
    "rollback-rate": "Rollback-Rate",
    "rollback-rework-delta": "Rollback-Rework-Delta",
}


def _render(*, ladder_name: str, header: dict[str, str], values: dict[str, str]) -> str:
    lines = [
        f"# Threshold Sign-off: {ladder_name}",
        "",
        f"Approved: {header['approved']}",
        f"Decision-Owner: {header['decision-owner']}",
        f"Decision-Date: {header['decision-date']}",
        "",
    ]
    lines += [f"{_LABELS[key]}: {values[key]}" for key in _LABELS]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draft docs/adr/ADR-021-threshold-signoff.md from the current thresholds config."
    )
    parser.add_argument(
        "--thresholds", default="tools/ci/config/enforcement_ladder_thresholds.json"
    )
    parser.add_argument("--signoff", default="docs/adr/ADR-021-threshold-signoff.md")
    parser.add_argument("--ladder-name", default="progressive-enforcement-ladder")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the draft without writing it."
    )
    args = parser.parse_args()

    cfg_path = Path(args.thresholds)
    signoff_path = Path(args.signoff)

    if not cfg_path.exists():
        print(f"ERROR: thresholds file not found: {cfg_path}")
        return 1

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    expected = _expected_pairs(cfg)
    existing = _parse_kv(signoff_path)

    if existing and _thresholds_unchanged(existing, expected):
        # Numerically identical — reuse the existing file's own value strings
        # (e.g. "0.10") instead of a freshly stringified float ("0.1"), so an
        # unchanged config never produces a cosmetic diff on a signed document.
        header = {key: existing.get(key, "") for key in _HEADER_KEYS}
        values = {key: existing.get(key, expected[key]) for key in expected}
        print(
            f"No threshold change detected; preserving existing sign-off from {signoff_path}."
        )
    else:
        header = {
            "approved": _PLACEHOLDER_APPROVED,
            "decision-owner": _PLACEHOLDER_OWNER,
            "decision-date": _PLACEHOLDER_DATE,
        }
        values = expected
        if existing:
            print(
                "Thresholds changed since the last sign-off — resetting Approved/"
                "Decision-Owner/Decision-Date; a human must re-approve before this "
                "passes check_enforcement_threshold_signoff.py."
            )
        else:
            print(f"No existing sign-off found at {signoff_path}; drafting a new one.")

    draft = _render(ladder_name=args.ladder_name, header=header, values=values)

    if args.dry_run:
        print("\n--- draft ---")
        print(draft)
        return 0

    signoff_path.parent.mkdir(parents=True, exist_ok=True)
    signoff_path.write_text(draft, encoding="utf-8")
    print(f"Wrote draft to {signoff_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
