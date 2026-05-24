from __future__ import annotations

from tools.ci import enforcement_ladder_digest as d


def test_compute_metrics_empty() -> None:
    m = d._compute_metrics([])
    assert m.sample_size == 0
    assert m.avg_false_block_rate == 0.0


def test_evaluate_promote_ready() -> None:
    metrics = d.LadderMetrics(
        sample_size=6,
        avg_false_block_rate=0.1,
        avg_rework_delta=-0.05,
        rollback_rate=0.0,
    )
    thresholds = {
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
    out = d._evaluate(metrics, thresholds)
    assert out["promote_ready"] is True
    assert out["rollback_recommended"] is False


def test_evaluate_rollback_recommended() -> None:
    metrics = d.LadderMetrics(
        sample_size=4,
        avg_false_block_rate=0.35,
        avg_rework_delta=0.2,
        rollback_rate=0.5,
    )
    thresholds = {
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
    out = d._evaluate(metrics, thresholds)
    assert out["rollback_recommended"] is True
