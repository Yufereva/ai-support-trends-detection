"""Simple privacy helpers for demo-safe ticket text."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
LONG_ID_RE = re.compile(r"\b(?:acct|account|customer|cust)[-_]?[A-Za-z0-9]{5,}\b", re.IGNORECASE)


def redact_text(value: str) -> str:
    text = str(value)
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = URL_RE.sub("[redacted-url]", text)
    text = LONG_ID_RE.sub("[redacted-id]", text)
    return text


def redact_ticket_text(subject: str, description: str) -> tuple[str, str]:
    return redact_text(subject), redact_text(description)
