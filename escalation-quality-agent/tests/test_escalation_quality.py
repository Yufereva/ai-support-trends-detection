import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import escalation_quality as eq


def _by_id(draft_id: str) -> dict:
    return next(d for d in eq.load_drafts() if d["id"] == draft_id)


def test_thresholds_are_explicit():
    assert eq.PASS_SCORE == 0.75
    assert eq.NEEDS_WORK_SCORE == 0.50
    assert eq.MIN_EVIDENCE_TICKETS == 3
    assert eq.MIN_SUMMARY_CHARS == 80


def test_known_good_draft_is_ready():
    report = eq.score_draft(_by_id("EQ-GOOD-001"))
    assert report["verdict"] == "ready"
    assert report["score"] >= eq.PASS_SCORE
    assert report["gaps"] == []
    assert "complete enough" in report["recommendation"].lower()


def test_known_weak_draft_needs_work():
    report = eq.score_draft(_by_id("EQ-WEAK-001"))
    assert report["verdict"] == "needs_work"
    gap_ids = {g["id"] for g in report["gaps"]}
    assert "expected_vs_actual" in gap_ids
    assert "repro_or_environment" in gap_ids
    # Typical Trend Detection shape: evidence + impact present, behavior/repro missing.
    assert "evidence" not in gap_ids
    assert "impact" not in gap_ids


def test_known_poor_draft_is_poor():
    report = eq.score_draft(_by_id("EQ-POOR-001"))
    assert report["verdict"] == "poor"
    gap_ids = {g["id"] for g in report["gaps"]}
    assert "title" in gap_ids
    assert "evidence" in gap_ids
    assert "impact" in gap_ids
    assert "trigger" in gap_ids


def test_live_trend_shape_typically_needs_work():
    report = eq.score_draft(_by_id("EQ-LIVE-SHAPE-001"))
    assert report["verdict"] == "needs_work"
    gap_ids = {g["id"] for g in report["gaps"]}
    assert gap_ids == {"expected_vs_actual", "repro_or_environment"}


def test_expected_verdicts_match_dataset_labels():
    for draft in eq.load_drafts():
        report = eq.score_draft(draft)
        assert report["verdict"] == draft["expected_verdict"], draft["id"]


def test_score_all_drafts_ranks_ready_first():
    reports = eq.score_all_drafts()
    verdicts = [r["verdict"] for r in reports]
    ranks = [eq.VERDICT_RANK[v] for v in verdicts]
    assert ranks == sorted(ranks, reverse=True)


def test_explicit_gap_note_satisfies_repro_check():
    draft = dict(_by_id("EQ-WEAK-001"))
    draft["summary"] = (
        draft["summary"]
        + "\n\nMissing reproduction steps — to be collected from the customer."
    )
    report = eq.score_draft(draft)
    repro = next(c for c in report["checks"] if c["id"] == "repro_or_environment")
    assert repro["passed"] is True


def test_format_quality_summary_includes_verdict_and_gaps():
    report = eq.score_draft(_by_id("EQ-POOR-001"))
    text = eq.format_quality_summary(report)
    assert "poor" in text
    assert "Gaps:" in text


def test_quality_panel_html_mentions_soft_gate_when_not_ready():
    report = eq.score_draft(_by_id("EQ-WEAK-001"))
    html = eq.quality_panel_html(report)
    assert "Escalation Quality" in html
    assert "Soft gate" in html
    assert "Needs work" in html


def test_quality_panel_html_ready_has_no_soft_gate_caveat():
    report = eq.score_draft(_by_id("EQ-GOOD-001"))
    html = eq.quality_panel_html(report)
    assert "Ready for Engineering" in html
    assert "Soft gate" not in html


def test_quality_panel_html_lists_all_checks_with_pass_and_gap():
    report = eq.score_draft(_by_id("EQ-LIVE-SHAPE-001"))
    html = eq.quality_panel_html(report)
    assert report["check_count"] == 8
    for check in report["checks"]:
        assert check["label"] in html
        assert check["detail"] in html
    assert html.count(">Pass<") == report["passed_count"]
    assert html.count(">Gap<") == len(report["gaps"])
    assert "Expected vs actual" in html
    assert "Repro / environment" in html


def test_quality_panel_html_compact_is_short_form():
    report = eq.score_draft(_by_id("EQ-WEAK-001"))
    compact = eq.quality_panel_html(report, compact=True)
    full = eq.quality_panel_html(report, compact=False)
    assert "Gaps:" in compact
    assert "Expected vs actual" in compact
    assert compact.count(">Pass<") == 0
    assert compact.count(">Gap<") == 0
    assert len(compact) < len(full)
    for check in report["checks"]:
        if check["passed"]:
            assert check["detail"] not in compact


def test_ready_requires_required_checks_even_if_score_high():
    """A draft cannot be 'ready' while a required check fails."""
    draft = dict(_by_id("EQ-GOOD-001"))
    draft["priority"] = ""
    report = eq.score_draft(draft)
    assert report["verdict"] != "ready"
    assert any(g["id"] == "priority" for g in report["gaps"])
