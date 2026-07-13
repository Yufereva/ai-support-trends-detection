"""End-to-end trend detection pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from support_trend_detection.clustering import assign_clusters, top_terms_for_cluster
from support_trend_detection.config import (
    DEFAULT_CURRENT_DAYS,
    DEFAULT_DATA_PATH,
    DEFAULT_MAX_TRENDS,
    DEFAULT_PREVIOUS_DAYS,
)
from support_trend_detection.ingestion import drop_duplicate_tickets, load_tickets, validate_tickets
from support_trend_detection.models import Trend
from support_trend_detection.preprocessing import prepare_ticket_text
from support_trend_detection.trend_scoring import score_trends


def run_pipeline(
    data: str | Path | pd.DataFrame = DEFAULT_DATA_PATH,
    current_days: int = DEFAULT_CURRENT_DAYS,
    previous_days: int = DEFAULT_PREVIOUS_DAYS,
    max_trends: int = DEFAULT_MAX_TRENDS,
    reference_date: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, list[Trend]]:
    if isinstance(data, pd.DataFrame):
        tickets = validate_tickets(data)
    else:
        tickets = load_tickets(data)

    tickets = drop_duplicate_tickets(tickets)
    tickets = prepare_ticket_text(tickets)
    tickets = assign_clusters(tickets)
    terms = top_terms_for_cluster(tickets)
    trends = score_trends(
        tickets,
        top_terms=terms,
        current_days=current_days,
        previous_days=previous_days,
        max_trends=max_trends,
        reference_date=reference_date,
    )
    return tickets, trends
