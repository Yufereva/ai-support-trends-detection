"""Persist confirmed human reviews across Streamlit page navigation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REVIEW_PATH = ROOT / "data" / "runtime" / "trend_reviews.json"


def load_confirmed_review(ticket_id: str) -> dict | None:
    if not REVIEW_PATH.exists():
        return None
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    review = payload.get("reviews", {}).get(ticket_id)
    return dict(review) if review else None


def save_confirmed_review(ticket_id: str, review: dict) -> None:
    payload = {"reviews": {}}
    if REVIEW_PATH.exists():
        payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        payload.setdefault("reviews", {})
    payload["reviews"][ticket_id] = review

    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REVIEW_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(REVIEW_PATH)
