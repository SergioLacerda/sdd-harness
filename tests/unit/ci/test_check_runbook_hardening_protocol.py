from __future__ import annotations

from tools.ci.check_runbook_hardening_protocol import _is_iso_date


def test_is_iso_date() -> None:
    assert _is_iso_date("2026-05-24") is True
    assert _is_iso_date("2026/05/24") is False
