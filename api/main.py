"""FastAPI backend for Trend Detection — shared engine for Streamlit demo and ZAF sidebar."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from impact import calculate_customer_impact  # noqa: E402
from similarity import (  # noqa: E402
    MODEL_NAME,
    SIMILARITY_THRESHOLD,
    TREND_MIN_COUNT,
    TREND_WINDOW_DAYS,
    compute_embeddings,
    detect_trend,
    find_similar,
    format_engineering_ticket_text,
    generate_engineering_ticket,
    load_tickets,
)

app = FastAPI(title="Trend Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_cache() -> dict:
    return compute_embeddings()


def _encode_text(subject: str, body: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    text = f"{subject} {body}".strip()
    return model.encode([text], normalize_embeddings=True)[0]


def _similar_from_scores(
    cache: dict,
    scores: np.ndarray,
    exclude_idx: int | None = None,
    top_k: int = 5,
) -> list[dict]:
    ranked = np.argsort(scores)[::-1]
    results = []
    for i in ranked:
        if exclude_idx is not None and i == exclude_idx:
            continue
        results.append(
            {
                "id": cache["ids"][i],
                "subject": cache["subjects"][i],
                "category": cache["categories"][i],
                "created_at": cache["created_at"][i],
                "similarity": float(scores[i]),
            }
        )
        if len(results) >= top_k:
            break
    return results


def _trend_from_scores(
    cache: dict,
    scores: np.ndarray,
    exclude_idx: int | None,
    subject: str,
    category: str,
    threshold: float = SIMILARITY_THRESHOLD,
    min_count: int = TREND_MIN_COUNT,
    window_days: int = TREND_WINDOW_DAYS,
) -> dict:
    reference_time = max(
        datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        for value in cache["created_at"]
    )
    window_start = reference_time - timedelta(days=window_days)
    recent = np.array([
        window_start
        <= datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        <= reference_time
        for value in cache["created_at"]
    ])
    same_category = np.array(cache["categories"]) == category
    mask = (scores >= threshold) & same_category & recent
    if exclude_idx is not None:
        mask[exclude_idx] = False
    similar_count = int(mask.sum())
    similar_ids = [cache["ids"][i] for i in np.where(mask)[0]]
    return {
        "is_potential_trend": similar_count >= min_count,
        "similar_count": similar_count,
        "threshold": threshold,
        "min_count": min_count,
        "window_days": window_days,
        "similar_ids": similar_ids,
        "category": category,
        "subject": subject,
    }


def _build_response(
    cache: dict,
    similar: list[dict],
    trend: dict,
    ticket_id: str | None,
    trigger_label: str,
) -> dict[str, Any]:
    impact = calculate_customer_impact(trend["similar_ids"], ticket_id)
    engineering_draft = None
    engineering_draft_text = None
    if trend["is_potential_trend"] and ticket_id:
        engineering_draft = generate_engineering_ticket(
            cache, ticket_id, trend, similar, impact
        )
        engineering_draft_text = format_engineering_ticket_text(engineering_draft)
    elif trend["is_potential_trend"]:
        engineering_draft = {
            "title": (
                f"[Trend] Recurring {trend['category'].replace('_', ' ').title()} issues "
                f"({trend['similar_count']} similar tickets)"
            ),
            "summary": (
                f"Support trend detected from free-text input ({trigger_label}): "
                f"{trend['similar_count']} tickets with similarity >= {trend['threshold']:.0%}."
            ),
            "priority": "medium" if trend["similar_count"] >= 20 else "low",
            "category": trend["category"],
            "similar_ticket_ids": trend["similar_ids"][:20],
            "trigger_ticket_id": None,
            "similar_count": trend["similar_count"],
            "customer_impact": impact,
        }
        engineering_draft_text = format_engineering_ticket_text(engineering_draft)

    return {
        "ticket_id": ticket_id,
        "trigger": trigger_label,
        "similar_tickets": similar,
        "trend": trend,
        "impact": impact,
        "engineering_draft": engineering_draft,
        "engineering_draft_text": engineering_draft_text,
    }


class AnalyzeRequest(BaseModel):
    ticket_id: str | None = None
    subject: str | None = None
    body: str | None = None

    @model_validator(mode="after")
    def validate_input(self) -> AnalyzeRequest:
        if self.ticket_id:
            return self
        if self.subject and self.body:
            return self
        raise ValueError("Provide ticket_id or both subject and body")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict[str, Any]:
    tickets = {t["id"]: t for t in load_tickets()}
    ticket = tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict[str, Any]:
    cache = get_cache()

    if req.ticket_id:
        try:
            similar = find_similar(cache, req.ticket_id, top_k=5)
            trend = detect_trend(cache, req.ticket_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _build_response(cache, similar, trend, req.ticket_id, req.ticket_id)

    query = _encode_text(req.subject or "", req.body or "")
    scores = cache["embeddings"] @ query
    similar = _similar_from_scores(cache, scores, top_k=5)
    category = similar[0]["category"] if similar else "unknown"
    trend = _trend_from_scores(
        cache,
        scores,
        exclude_idx=None,
        subject=req.subject or "",
        category=category,
    )
    label = (req.subject or "")[:60]
    return _build_response(cache, similar, trend, None, label)


def _incoming_warning(result: dict[str, Any]) -> dict[str, Any]:
    trend = result["trend"]
    is_potential_trend = bool(trend["is_potential_trend"])
    return {
        "is_potential_trend": is_potential_trend,
        "label": "Potential trend" if is_potential_trend else None,
        "similar_count": trend["similar_count"],
        "threshold": trend["threshold"],
        "min_count": trend.get("min_count", TREND_MIN_COUNT),
        "window_days": trend.get("window_days", TREND_WINDOW_DAYS),
        "message": (
            f"Potential trend: {trend['similar_count']} similar tickets found "
            f"in the previous {trend.get('window_days', TREND_WINDOW_DAYS)} days."
            if is_potential_trend
            else "No trend signal detected."
        ),
    }


@app.post("/webhooks/tickets/incoming")
def analyze_incoming_ticket(req: AnalyzeRequest) -> dict[str, Any]:
    """Return the warning payload an intake integration can attach to a new ticket."""
    result = analyze(req)
    return {
        "event": "ticket.trend_checked",
        "ticket_id": result["ticket_id"],
        "warning": _incoming_warning(result),
        "analysis": result,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
