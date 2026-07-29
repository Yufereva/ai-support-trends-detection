import numpy as np
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import _incoming_warning


def test_incoming_warning_returns_ticket_badge_payload():
    result = {
        "trend": {
            "is_potential_trend": True,
            "similar_count": 13,
            "threshold": 0.60,
            "min_count": 3,
            "window_days": 7,
        }
    }

    warning = _incoming_warning(result)

    assert warning == {
        "is_potential_trend": True,
        "label": "Potential trend",
        "similar_count": 13,
        "threshold": 0.60,
        "min_count": 3,
        "window_days": 7,
        "message": "Potential trend: 13 similar tickets found in the previous 7 days.",
    }


def test_incoming_webhook_runs_automatic_trend_check(monkeypatch):
    cache = {
        "ids": ["previous-1", "previous-2", "previous-3", "trigger"],
        "embeddings": np.array([[1.0, 0.0]] * 4),
        "subjects": ["Production API key rejected"] * 4,
        "categories": ["api"] * 4,
        "priorities": ["high"] * 4,
        "created_at": [
            "2026-07-07T09:00:00",
            "2026-07-08T09:00:00",
            "2026-07-09T09:00:00",
            "2026-07-10T09:00:00",
        ],
    }
    monkeypatch.setattr(api_main, "active_cache", lambda: cache)
    monkeypatch.setattr(api_main, "calculate_customer_impact", lambda *_: {})
    monkeypatch.setattr(
        api_main,
        "generate_engineering_ticket",
        lambda *_: {"title": "Trend draft", "similar_count": 3},
    )
    monkeypatch.setattr(
        api_main,
        "format_engineering_ticket_text",
        lambda _: "Trend draft text",
    )

    response = TestClient(api_main.app).post(
        "/webhooks/tickets/incoming",
        json={"ticket_id": "trigger"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event"] == "ticket.trend_checked"
    assert payload["warning"]["is_potential_trend"] is True
    assert payload["warning"]["similar_count"] == 3
    assert payload["analysis"]["trend"]["similar_ids"] == [
        "previous-1",
        "previous-2",
        "previous-3",
    ]
    assert payload["analysis"]["engineering_draft_text"] == "Trend draft text"
