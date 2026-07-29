"""Import bridge so Trend Detection can score drafts via Escalation Quality."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_EQ_MODULE_PATH = (
    Path(__file__).resolve().parent
    / "escalation-quality-agent"
    / "escalation_quality.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_escalation_quality_agent",
    _EQ_MODULE_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load Escalation Quality module from {_EQ_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

format_quality_summary = _MODULE.format_quality_summary
quality_panel_html = _MODULE.quality_panel_html
score_draft = _MODULE.score_draft

__all__ = ["score_draft", "format_quality_summary", "quality_panel_html"]
