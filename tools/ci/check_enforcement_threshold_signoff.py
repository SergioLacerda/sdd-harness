#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class PromotionThreshold(TypedDict):
    min_samples: int
    max_false_block_rate: float
    max_rollback_rate: float
    max_rework_delta: float


class RollbackThreshold(TypedDict):
    min_samples: int
    false_block_rate: float
    rollback_rate: float
    rework_delta: float


class LadderThresholds(TypedDict):
    window_days: int
    promotion_candidate: PromotionThreshold
    rollback_trigger: RollbackThreshold


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


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _parse_thresholds(path: Path) -> LadderThresholds:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("thresholds payload must be a JSON object")
    p_raw = raw.get("promotion_candidate", {})
    r_raw = raw.get("rollback_trigger", {})
    if not isinstance(p_raw, dict) or not isinstance(r_raw, dict):
        raise ValueError("threshold sections must be JSON objects")
    return LadderThresholds(
        window_days=int(raw.get("window_days", 7)),
        promotion_candidate=PromotionThreshold(
            min_samples=int(p_raw.get("min_samples", 0)),
            max_false_block_rate=_as_float(p_raw.get("max_false_block_rate", 1.0), 1.0),
            max_rollback_rate=_as_float(p_raw.get("max_rollback_rate", 1.0), 1.0),
            max_rework_delta=_as_float(p_raw.get("max_rework_delta", 1.0), 1.0),
        ),
        rollback_trigger=RollbackThreshold(
            min_samples=int(r_raw.get("min_samples", 0)),
            false_block_rate=_as_float(r_raw.get("false_block_rate", 1.0), 1.0),
            rollback_rate=_as_float(r_raw.get("rollback_rate", 1.0), 1.0),
            rework_delta=_as_float(r_raw.get("rework_delta", 1.0), 1.0),
        ),
    )


def _expected_pairs(cfg: LadderThresholds) -> dict[str, str]:
    p = cfg["promotion_candidate"]
    r = cfg["rollback_trigger"]
    return {
        "window-days": str(cfg["window_days"]),
        "promotion-min-samples": str(p["min_samples"]),
        "promotion-max-false-block-rate": str(p["max_false_block_rate"]),
        "promotion-max-rollback-rate": str(p["max_rollback_rate"]),
        "promotion-max-rework-delta": str(p["max_rework_delta"]),
        "rollback-min-samples": str(r["min_samples"]),
        "rollback-false-block-rate": str(r["false_block_rate"]),
        "rollback-rate": str(r["rollback_rate"]),
        "rollback-rework-delta": str(r["rework_delta"]),
    }


def _is_numeric(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def _looks_like_placeholder_owner(owner: str) -> bool:
    normalized = owner.strip().lower()
    return normalized in {
        "",
        "owner",
        "governance-owner",
        "tbd",
        "todo",
        "unknown",
        "n/a",
        "na",
    }


def _valid_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate enforcement threshold sign-off."
    )
    parser.add_argument(
        "--thresholds",
        default="tools/ci/config/enforcement_ladder_thresholds.json",
    )
    parser.add_argument(
        "--signoff",
        default=".analysis/done/progressive-enforcement-ladder/threshold-signoff.md",
    )
    return parser.parse_args()


def _validate_required_files(cfg_path: Path, signoff_path: Path) -> int:
    if not cfg_path.exists():
        print(f"FAIL: THRESHOLD_SIGNOFF_VIOLATION: thresholds file missing: {cfg_path}")
        return 1
    if not signoff_path.exists():
        print(
            f"FAIL: THRESHOLD_SIGNOFF_VIOLATION: signoff file missing: {signoff_path}"
        )
        return 1
    return 0


def _validate_headers(signoff: dict[str, str]) -> int:
    required_headers = ["approved", "decision-owner", "decision-date"]
    missing_headers = [k for k in required_headers if not signoff.get(k, "")]
    if missing_headers:
        print(
            "FAIL: THRESHOLD_SIGNOFF_VIOLATION: missing required signoff fields: "
            + ", ".join(missing_headers)
        )
        return 1

    if signoff["approved"].strip().lower() not in {"yes", "true", "approved"}:
        print("FAIL: THRESHOLD_SIGNOFF_VIOLATION: Approved must be yes/true/approved")
        return 1
    if _looks_like_placeholder_owner(signoff["decision-owner"]):
        print(
            "FAIL: THRESHOLD_SIGNOFF_VIOLATION: Decision-Owner must be a real reviewer identity"
        )
        return 1
    if not _valid_iso_date(signoff["decision-date"]):
        print(
            "FAIL: THRESHOLD_SIGNOFF_VIOLATION: Decision-Date must be ISO date YYYY-MM-DD"
        )
        return 1
    return 0


def _collect_mismatches(signoff: dict[str, str], expected: dict[str, str]) -> list[str]:
    mismatches: list[str] = []
    for key, value in expected.items():
        actual = signoff.get(key, "")
        if _is_numeric(value) and _is_numeric(actual):
            if float(actual) != float(value):
                mismatches.append(f"{key}: expected={value} actual={actual}")
            continue
        if actual != value:
            mismatches.append(f"{key}: expected={value} actual={actual or '<missing>'}")
    return mismatches


def main() -> int:
    args = _parse_args()
    cfg_path = Path(args.thresholds)
    signoff_path = Path(args.signoff)

    file_status = _validate_required_files(cfg_path, signoff_path)
    if file_status != 0:
        return file_status

    cfg = _parse_thresholds(cfg_path)
    signoff = _parse_kv(signoff_path)
    header_status = _validate_headers(signoff)
    if header_status != 0:
        return header_status

    expected = _expected_pairs(cfg)
    mismatches = _collect_mismatches(signoff, expected)

    if mismatches:
        print("FAIL: THRESHOLD_SIGNOFF_VIOLATION: signoff values out of sync")
        for row in mismatches:
            print(f"  - {row}")
        return 1

    print("PASS: THRESHOLD_SIGNOFF_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
