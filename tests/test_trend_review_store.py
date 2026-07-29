import trend_review_store


def test_confirmed_review_round_trips_through_runtime_file(monkeypatch):
    review_path = trend_review_store.ROOT / "data" / "runtime" / "test-trend-reviews.json"
    review_path.unlink(missing_ok=True)
    monkeypatch.setattr(trend_review_store, "REVIEW_PATH", review_path)
    review = {
        "trend": {"similar_ids": ["T-1", "T-2"], "similar_count": 2},
        "draft": {"title": "Reviewed cluster"},
        "included_signature": ("T-1", "T-2"),
    }

    try:
        trend_review_store.save_confirmed_review("T-3", review)
        loaded = trend_review_store.load_confirmed_review("T-3")

        assert loaded["trend"]["similar_ids"] == ["T-1", "T-2"]
        assert loaded["draft"]["title"] == "Reviewed cluster"
        assert loaded["included_signature"] == ["T-1", "T-2"]
    finally:
        review_path.unlink(missing_ok=True)
