"""Import bridge so Trend Detection can score drafts via Escalation Quality."""

from __future__ import annotations

from escalation_quality import (
    format_quality_summary,
    quality_panel_html,
    score_draft,
)

__all__ = ["score_draft", "format_quality_summary", "quality_panel_html"]
