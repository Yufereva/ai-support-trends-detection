"""Dataset loading and schema validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "ticket_id",
    "created_at",
    "subject",
    "description",
    "product_area",
    "customer_tier",
    "priority",
    "status",
    "channel",
    "tags",
}


def load_tickets(path: str | Path) -> pd.DataFrame:
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    tickets = pd.read_csv(data_path)
    return validate_tickets(tickets)


def validate_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS - set(tickets.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    cleaned = tickets.copy()
    cleaned["created_at"] = pd.to_datetime(cleaned["created_at"], errors="coerce")
    if cleaned["created_at"].isna().any():
        raise ValueError("Dataset contains invalid created_at values")

    text_columns = [
        "ticket_id",
        "subject",
        "description",
        "product_area",
        "customer_tier",
        "priority",
        "status",
        "channel",
        "tags",
    ]
    for column in text_columns:
        cleaned[column] = cleaned[column].fillna("").astype(str).str.strip()

    empty_ticket_ids = cleaned["ticket_id"].eq("")
    if empty_ticket_ids.any():
        raise ValueError("Dataset contains empty ticket_id values")

    return cleaned.sort_values(["created_at", "ticket_id"]).reset_index(drop=True)


def drop_duplicate_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    return (
        tickets.sort_values(["created_at", "ticket_id"])
        .drop_duplicates(subset=["ticket_id"], keep="last")
        .reset_index(drop=True)
    )
