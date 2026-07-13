from support_trend_detection.trend_scoring import (
    classify_trend,
    growth_rate,
    priority_for_trend,
)


def test_growth_rate_handles_zero_previous_volume() -> None:
    assert growth_rate(5, 0) == 5.0
    assert growth_rate(0, 0) == 0.0


def test_classify_trend_identifies_emerging_product_issue() -> None:
    assert classify_trend(25, 10, 1.5) == "Emerging product issue"


def test_priority_accounts_for_enterprise_impact() -> None:
    assert priority_for_trend(25, 1.0, 12) == "P1"
    assert priority_for_trend(16, 0.6, 2) == "P2"
