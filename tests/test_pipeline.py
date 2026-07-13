from pathlib import Path

from support_trend_detection.pipeline import run_pipeline


def test_pipeline_detects_growing_synthetic_trends() -> None:
    tickets, trends = run_pipeline(Path("data/sample_tickets.csv"))

    assert len(tickets) >= 300
    assert len(trends) >= 2
    assert any("CSV" in trend.title for trend in trends)
    assert any("SSO" in trend.title for trend in trends)
    assert any(trend.enterprise_ticket_count > 0 for trend in trends)


def test_pipeline_output_is_deterministic() -> None:
    _, first = run_pipeline(Path("data/sample_tickets.csv"))
    _, second = run_pipeline(Path("data/sample_tickets.csv"))

    assert [trend.to_dict() for trend in first] == [trend.to_dict() for trend in second]
