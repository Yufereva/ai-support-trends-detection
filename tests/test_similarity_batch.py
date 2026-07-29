import sys
from types import SimpleNamespace

import numpy as np

import similarity
from similarity import (
    compute_embeddings,
    detect_trends_batch,
    score_similar_tickets,
    ticket_db_fingerprint,
)


def test_ticket_db_fingerprint_changes_when_membership_changes(tmp_path):
    db_path = tmp_path / "tickets.db"
    connection = __import__("sqlite3").connect(db_path)
    connection.execute("CREATE TABLE tickets (id TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO tickets (id) VALUES ('T-1'), ('T-30001')")
    connection.commit()
    before = ticket_db_fingerprint(db_path)

    connection.execute("INSERT INTO tickets (id) VALUES ('T-30002')")
    connection.commit()
    connection.close()
    after = ticket_db_fingerprint(db_path)

    assert before != after
    assert ticket_db_fingerprint(tmp_path / "missing.db") == "missing"


def test_score_similar_tickets_returns_only_requested_candidates():
    cache = {
        "ids": ["T-1", "T-2", "T-3"],
        "embeddings": np.array(
            [
                [1.0, 0.0],
                [0.8, 0.6],
                [0.0, 1.0],
            ]
        ),
    }

    scores = score_similar_tickets(cache, "T-1", ["T-2", "T-missing"])

    assert scores == {"T-2": 0.8}


def test_detect_trends_batch_flags_only_matching_tickets():
    cache = {
        "ids": ["T-1", "T-2", "T-3"],
        "embeddings": np.array(
            [
                [1.0, 0.0],
                [0.995, 0.1],
                [0.0, 1.0],
            ]
        ),
        "subjects": ["API key", "API token", "Invoice"],
        "categories": ["api", "api", "billing"],
        "created_at": ["2026-07-01T09:00:00", "2026-07-01T10:00:00", "2026-07-01T11:00:00"],
    }

    signals = detect_trends_batch(
        cache,
        ("T-1", "T-2", "T-3"),
        threshold=0.9,
        min_count=1,
    )

    assert signals["T-1"]["is_potential_trend"] is False
    assert signals["T-1"]["similar_count"] == 0
    assert signals["T-2"]["is_potential_trend"] is True
    assert signals["T-2"]["similar_count"] == 1
    assert signals["T-3"]["is_potential_trend"] is False


def test_detect_trends_batch_ignores_future_and_old_matches():
    cache = {
        "ids": ["old", "previous", "trigger", "future"],
        "embeddings": np.array([[1.0, 0.0]] * 4),
        "subjects": ["API key"] * 4,
        "categories": ["api"] * 4,
        "created_at": [
            "2026-06-01T09:00:00",
            "2026-07-09T09:00:00",
            "2026-07-10T09:00:00",
            "2026-07-11T09:00:00",
        ],
    }

    signal = detect_trends_batch(
        cache, ("trigger",), threshold=0.9, min_count=1, window_days=7
    )["trigger"]

    assert signal["similar_count"] == 1
    assert signal["is_potential_trend"] is True


def test_detect_trends_batch_handles_empty_queue():
    assert detect_trends_batch({}, ()) == {}


def test_detect_trends_batch_skips_ids_missing_from_cache():
    cache = {
        "ids": ["T-1", "T-2"],
        "embeddings": np.array(
            [
                [1.0, 0.0],
                [0.995, 0.1],
            ]
        ),
        "subjects": ["API key", "API token"],
        "categories": ["api", "api"],
        "created_at": ["2026-07-01T09:00:00", "2026-07-01T10:00:00"],
    }

    signals = detect_trends_batch(
        cache,
        ("T-1", "T-30026", "T-2"),
        threshold=0.9,
        min_count=1,
    )

    assert "T-30026" not in signals
    assert signals["T-2"]["is_potential_trend"] is True


def test_compute_embeddings_includes_every_shared_ticket(tmp_path, monkeypatch):
    tickets = [
        {
            "id": "T-1",
            "subject": "API issue",
            "body": "Production request fails",
            "category": "api",
            "priority": "high",
            "created_at": "2026-07-01T09:00:00",
            "tags": ["api"],
        },
        {
            "id": "T-30026",
            "subject": "How do I export data?",
            "body": "I cannot find the documentation",
            "category": "documentation",
            "priority": "medium",
            "created_at": "2026-07-01T10:00:00",
            "tags": ["knowledge-gap", "doc-question"],
        },
    ]

    class FakeModel:
        def __init__(self, _name):
            pass

        def encode(self, texts, **_kwargs):
            return np.array([[1.0, 0.0] for _ in texts])

    monkeypatch.setattr(similarity, "CACHE_PATH", tmp_path / "embeddings_cache.npz")
    monkeypatch.setattr(similarity, "RUNTIME_PATH", tmp_path)
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeModel),
    )

    cache = compute_embeddings(tickets=tickets)

    assert cache["ids"] == ["T-1", "T-30026"]


def test_detect_trends_batch_does_not_mix_categories():
    cache = {
        "ids": ["api-1", "api-2", "billing-1", "trigger"],
        "embeddings": np.array([[1.0, 0.0]] * 4),
        "subjects": ["Credential issue"] * 4,
        "categories": ["api", "api", "billing", "api"],
        "created_at": [
            "2026-07-08T09:00:00",
            "2026-07-09T09:00:00",
            "2026-07-09T12:00:00",
            "2026-07-10T09:00:00",
        ],
    }

    signal = detect_trends_batch(
        cache, ("trigger",), threshold=0.9, min_count=3, window_days=7
    )["trigger"]

    assert signal["similar_count"] == 2
    assert signal["is_potential_trend"] is False
