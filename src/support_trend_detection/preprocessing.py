"""Text preprocessing for deterministic trend detection."""

from __future__ import annotations

import re

import pandas as pd

from support_trend_detection.privacy import redact_text

NON_WORD_RE = re.compile(r"[^a-z0-9\s]+")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = redact_text(value).lower()
    text = NON_WORD_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def prepare_ticket_text(tickets: pd.DataFrame) -> pd.DataFrame:
    prepared = tickets.copy()
    prepared["safe_subject"] = prepared["subject"].map(redact_text)
    prepared["safe_description"] = prepared["description"].map(redact_text)
    combined = (
        prepared["safe_subject"]
        + " "
        + prepared["safe_description"]
        + " "
        + prepared["product_area"]
        + " "
        + prepared["tags"]
    )
    prepared["analysis_text"] = combined.map(normalize_text)
    return prepared
