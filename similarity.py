"""Embedding-based ticket similarity, trend detection, and engineering ticket drafts."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from impact import calculate_customer_impact

ROOT = Path(__file__).resolve().parent
RUNTIME_PATH = ROOT / "data" / "runtime"
DB_PATH = RUNTIME_PATH / "tickets.db"
CACHE_PATH = RUNTIME_PATH / "embeddings_cache.npz"

SIMILARITY_THRESHOLD = 0.60
TREND_MIN_COUNT = 3
TREND_WINDOW_DAYS = 7
MODEL_NAME = "all-MiniLM-L6-v2"


def load_tickets(db_path: Path | None = None) -> list[dict]:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, created_at, subject, body, category, priority, status, "
        "customer_tier, tags, cluster FROM tickets ORDER BY id"
    ).fetchall()
    conn.close()

    tickets = []
    for row in rows:
        ticket = dict(row)
        try:
            ticket["tags"] = json.loads(ticket["tags"])
        except (json.JSONDecodeError, TypeError):
            ticket["tags"] = []
        tickets.append(ticket)
    return tickets


def _ticket_text(ticket: dict) -> str:
    return f"{ticket['subject']} {ticket['body']}"


def compute_embeddings(
    tickets: list[dict] | None = None,
    force_recompute: bool = False,
) -> dict:
    if tickets is None:
        tickets = load_tickets()

    if not force_recompute and CACHE_PATH.exists():
        data = np.load(CACHE_PATH, allow_pickle=True)
        cached = {
            "ids": data["ids"].tolist(),
            "embeddings": data["embeddings"],
            "subjects": data["subjects"].tolist(),
            "categories": data["categories"].tolist(),
            "priorities": data["priorities"].tolist(),
            "created_at": data["created_at"].tolist(),
        }
        if cached["ids"] == [ticket["id"] for ticket in tickets]:
            return cached

    from sentence_transformers import SentenceTransformer

    RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(MODEL_NAME)
    texts = [_ticket_text(t) for t in tickets]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    cache = {
        "ids": [t["id"] for t in tickets],
        "embeddings": embeddings,
        "subjects": [t["subject"] for t in tickets],
        "categories": [t["category"] for t in tickets],
        "priorities": [t["priority"] for t in tickets],
        "created_at": [t["created_at"] for t in tickets],
    }
    np.savez(
        CACHE_PATH,
        ids=np.array(cache["ids"]),
        embeddings=cache["embeddings"],
        subjects=np.array(cache["subjects"], dtype=object),
        categories=np.array(cache["categories"], dtype=object),
        priorities=np.array(cache["priorities"], dtype=object),
        created_at=np.array(cache["created_at"], dtype=object),
    )
    return cache


def _index_for_id(cache: dict, ticket_id: str) -> int:
    try:
        return cache["ids"].index(ticket_id)
    except ValueError as exc:
        raise ValueError(f"Ticket {ticket_id} not found in cache") from exc


def _similarity_scores(cache: dict, idx: int) -> np.ndarray:
    query = cache["embeddings"][idx]
    return cache["embeddings"] @ query


def _created_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _previous_window_mask(cache: dict, idx: int, window_days: int) -> np.ndarray:
    trigger_time = _created_at(cache["created_at"][idx])
    window_start = trigger_time - timedelta(days=window_days)
    return np.array([
        window_start <= _created_at(created_at) < trigger_time
        for created_at in cache["created_at"]
    ])


def find_similar(cache: dict, ticket_id: str, top_k: int = 5) -> list[dict]:
    idx = _index_for_id(cache, ticket_id)
    scores = _similarity_scores(cache, idx)

    ranked = np.argsort(scores)[::-1]
    results = []
    for i in ranked:
        if i == idx:
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


def detect_trend(
    cache: dict,
    ticket_id: str,
    threshold: float = SIMILARITY_THRESHOLD,
    min_count: int = TREND_MIN_COUNT,
    window_days: int = TREND_WINDOW_DAYS,
) -> dict:
    idx = _index_for_id(cache, ticket_id)
    scores = _similarity_scores(cache, idx)
    same_category = np.array(cache["categories"]) == cache["categories"][idx]
    mask = (
        (scores >= threshold)
        & same_category
        & _previous_window_mask(cache, idx, window_days)
    )
    mask[idx] = False
    similar_count = int(mask.sum())
    similar_ids = [cache["ids"][i] for i in np.where(mask)[0]]

    return {
        "is_potential_trend": similar_count >= min_count,
        "similar_count": similar_count,
        "threshold": threshold,
        "min_count": min_count,
        "window_days": window_days,
        "similar_ids": similar_ids,
        "category": cache["categories"][idx],
        "subject": cache["subjects"][idx],
    }


def detect_trends_batch(
    cache: dict,
    ticket_ids: list[str] | tuple[str, ...],
    threshold: float = SIMILARITY_THRESHOLD,
    min_count: int = TREND_MIN_COUNT,
    window_days: int = TREND_WINDOW_DAYS,
) -> dict[str, dict]:
    """Check selected tickets against the full history in one matrix operation."""
    if not ticket_ids:
        return {}

    indices = [_index_for_id(cache, ticket_id) for ticket_id in ticket_ids]
    queries = cache["embeddings"][indices]
    scores = cache["embeddings"] @ queries.T
    matches = scores >= threshold

    results = {}
    for column, (ticket_id, idx) in enumerate(zip(ticket_ids, indices, strict=True)):
        same_category = np.array(cache["categories"]) == cache["categories"][idx]
        ticket_matches = (
            matches[:, column]
            & same_category
            & _previous_window_mask(cache, idx, window_days)
        )
        ticket_matches[idx] = False
        similar_count = int(ticket_matches.sum())
        results[ticket_id] = {
            "is_potential_trend": similar_count >= min_count,
            "similar_count": similar_count,
            "threshold": threshold,
            "min_count": min_count,
            "window_days": window_days,
            "category": cache["categories"][idx],
            "subject": cache["subjects"][idx],
        }
    return results


def score_similar_tickets(
    cache: dict,
    ticket_id: str,
    candidate_ids: list[str],
) -> dict[str, float]:
    """Return exact embedding similarity scores for a reviewed candidate set."""
    query_idx = _index_for_id(cache, ticket_id)
    scores = _similarity_scores(cache, query_idx)
    index_by_id = {candidate_id: idx for idx, candidate_id in enumerate(cache["ids"])}
    return {
        candidate_id: float(scores[index_by_id[candidate_id]])
        for candidate_id in candidate_ids
        if candidate_id in index_by_id and candidate_id != ticket_id
    }


def generate_engineering_ticket(
    cache: dict,
    ticket_id: str,
    trend: dict,
    similar_top: list[dict],
    impact: dict | None = None,
) -> dict:
    idx = _index_for_id(cache, ticket_id)
    category = cache["categories"][idx]
    priority = cache["priorities"][idx]

    if impact is None:
        impact = calculate_customer_impact(trend["similar_ids"], ticket_id)

    sample_subjects = [s["subject"] for s in similar_top[:3]]
    cluster_label = category.replace("_", " ").title()
    enterprise_count = impact["by_tier"].get("enterprise", 0)

    title = f"[Trend] Recurring {cluster_label} issues ({trend['similar_count']} similar tickets)"
    summary = (
        f"Support trend detected: {trend['similar_count']} tickets with similarity "
        f">= {trend['threshold']:.0%} to ticket {ticket_id}.\n\n"
        f"Category: {category}\n"
        f"Trigger ticket: {trend['subject']}\n\n"
        f"Customer impact:\n"
        f"- {impact['total_tickets']} tickets, {impact['unique_accounts']} unique accounts, "
        f"{enterprise_count} enterprise\n"
        f"- Est. ARR at risk: {impact['arr_at_risk_formatted']} (Salesforce)\n\n"
        f"Sample subjects:\n"
        + "\n".join(f"- {s}" for s in sample_subjects)
        + f"\n\nRecommend engineering review for potential systemic {category} issue."
    )

    return {
        "title": title,
        "summary": summary,
        "priority": _elevated_priority(priority, trend["similar_count"]),
        "category": category,
        "similar_ticket_ids": trend["similar_ids"][:20],
        "trigger_ticket_id": ticket_id,
        "similar_count": trend["similar_count"],
        "customer_impact": impact,
    }


def _elevated_priority(base: str, count: int) -> str:
    base = base.lower()
    if count >= 50 or base == "urgent":
        return "urgent"
    if count >= 20 or base == "high":
        return "high"
    if base == "medium":
        return "medium"
    return base


PRIORITY_DISPLAY = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "urgent": "Urgent",
}


def _priority_display(priority: str) -> str:
    return PRIORITY_DISPLAY.get(priority.lower(), priority.replace("_", " ").title())


def format_engineering_ticket_text(draft: dict) -> str:
    ids_text = ", ".join(draft["similar_ticket_ids"])
    impact = draft.get("customer_impact", {})
    impact_line = ""
    if impact:
        enterprise_count = impact.get("by_tier", {}).get("enterprise", 0)
        impact_line = (
            f"\nCustomer impact:\n"
            f"- {impact.get('total_tickets', 0)} tickets, "
            f"{impact.get('unique_accounts', 0)} unique accounts, "
            f"{enterprise_count} enterprise\n"
            f"- Est. ARR at risk: {impact.get('arr_at_risk_formatted', '$0')} (Salesforce)\n"
        )
    return (
        f"Title: {draft['title']}\n\n"
        f"Priority: {_priority_display(draft['priority'])}\n"
        f"Category: {draft['category']}\n"
        f"{impact_line}\n"
        f"Summary:\n{draft['summary']}\n\n"
        f"Similar ticket IDs ({draft['similar_count']} total, showing up to 20):\n{ids_text}"
    )
