from pathlib import Path

import pandas as pd
import pytest

from support_trend_detection.ingestion import (
    drop_duplicate_tickets,
    load_tickets,
    validate_tickets,
)


def test_load_synthetic_dataset() -> None:
    tickets = load_tickets(Path("data/sample_tickets.csv"))

    assert len(tickets) >= 300
    assert tickets["ticket_id"].is_unique
    assert pd.api.types.is_datetime64_any_dtype(tickets["created_at"])


def test_validate_tickets_rejects_missing_required_column() -> None:
    tickets = pd.DataFrame({"ticket_id": ["TCK-1"]})

    with pytest.raises(ValueError, match="missing required columns"):
        validate_tickets(tickets)


def test_drop_duplicate_tickets_keeps_last_record() -> None:
    tickets = load_tickets(Path("data/sample_tickets.csv")).head(2)
    duplicate = tickets.iloc[[0]].copy()
    duplicate["subject"] = "Updated subject"
    combined = pd.concat([tickets, duplicate], ignore_index=True)

    deduped = drop_duplicate_tickets(combined)

    assert len(deduped) == 2
    assert "Updated subject" in deduped["subject"].to_list()
