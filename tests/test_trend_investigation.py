from trend_view import (
    _build_operational_events,
    _reviewed_trend,
    _similarity_explanation,
)


def test_similarity_explanation_uses_shared_category_and_signals():
    trigger = {
        "category": "identity",
        "tags": '["sso", "scim", "access-removal"]',
    }
    candidate = {
        "category": "identity",
        "tags": '["scim", "access-removal", "security"]',
    }

    explanation = _similarity_explanation(trigger, candidate)

    assert "same identity category" in explanation
    assert "ACCESS REMOVAL" in explanation
    assert "SCIM" in explanation


def test_reviewed_trend_recalculates_count_and_threshold():
    detected = {
        "similar_ids": ["T-1", "T-2", "T-3", "T-4"],
        "similar_count": 4,
        "is_potential_trend": True,
        "min_count": 3,
    }

    reviewed = _reviewed_trend(detected, ["T-1", "T-2"])

    assert reviewed["similar_ids"] == ["T-1", "T-2"]
    assert reviewed["similar_count"] == 2
    assert reviewed["is_potential_trend"] is False


def test_operational_timeline_labels_synthetic_context_and_confirmation():
    tickets = {
        "T-1": {
            "id": "T-1",
            "created_at": "2026-07-04T06:00:00",
            "subject": "First report",
        },
        "T-2": {
            "id": "T-2",
            "created_at": "2026-07-04T08:00:00",
            "subject": "Second report",
        },
        "T-3": {
            "id": "T-3",
            "created_at": "2026-07-04T10:00:00",
            "subject": "Third report",
        },
        "T-4": {
            "id": "T-4",
            "created_at": "2026-07-04T12:00:00",
            "subject": "Trigger report",
        },
    }

    markup = _build_operational_events(tickets, "identity", "T-4", confirmed=True)

    assert "SCIM authorization worker release" in markup
    assert "Synthetic operational marker" in markup
    assert "Trend threshold reached" in markup
    assert "Support review confirmed" in markup
