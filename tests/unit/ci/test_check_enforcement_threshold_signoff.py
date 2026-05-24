from __future__ import annotations

from tools.ci.check_enforcement_threshold_signoff import (
    _expected_pairs,
    _looks_like_placeholder_owner,
    _parse_kv,
    _valid_iso_date,
)


def test_parse_kv_reads_fields(tmp_path) -> None:
    p = tmp_path / "signoff.md"
    p.write_text("Approved: yes\nDecision-Owner: owner\n", encoding="utf-8")
    data = _parse_kv(p)
    assert data["approved"] == "yes"
    assert data["decision-owner"] == "owner"


def test_expected_pairs_from_cfg() -> None:
    cfg = {
        "window_days": 7,
        "promotion_candidate": {
            "min_samples": 5,
            "max_false_block_rate": 0.15,
            "max_rollback_rate": 0.1,
            "max_rework_delta": 0.0,
        },
        "rollback_trigger": {
            "min_samples": 3,
            "false_block_rate": 0.3,
            "rollback_rate": 0.25,
            "rework_delta": 0.1,
        },
    }
    pairs = _expected_pairs(cfg)
    assert pairs["window-days"] == "7"
    assert pairs["promotion-max-false-block-rate"] == "0.15"
    assert pairs["rollback-rate"] == "0.25"


def test_placeholder_owner_detection() -> None:
    assert _looks_like_placeholder_owner("governance-owner") is True
    assert _looks_like_placeholder_owner("Sergio Lacerda") is False


def test_valid_iso_date() -> None:
    assert _valid_iso_date("2026-05-24") is True
    assert _valid_iso_date("24-05-2026") is False
