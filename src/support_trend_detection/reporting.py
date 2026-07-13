"""Report formatting helpers."""

from __future__ import annotations

import json
from pathlib import Path

from support_trend_detection.models import Trend


def trends_to_json(trends: list[Trend]) -> str:
    return json.dumps([trend.to_dict() for trend in trends], indent=2)


def trend_to_markdown(trend: Trend) -> str:
    growth_pct = round(trend.growth_rate * 100)
    tickets = ", ".join(trend.supporting_ticket_ids)
    return f"""# {trend.title}

**Classification:** {trend.classification}

**Evidence**
- {trend.current_volume} related tickets in the current period
- {trend.previous_volume} related tickets in the prior period
- {growth_pct}% period-over-period growth
- {trend.enterprise_ticket_count} enterprise-tier tickets represented
- Product areas: {", ".join(trend.product_areas)}

**Customer impact**
{trend.customer_impact}

**Recommended action**
{trend.recommended_action}

**Suggested priority:** {trend.priority}

**Confidence:** {trend.confidence}

{trend.confidence_reason}

**Supporting tickets:** {tickets}
"""


def write_example_outputs(trends: list[Trend], output_dir: str | Path) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "example_output.json").write_text(trends_to_json(trends), encoding="utf-8")
    if trends:
        (path / "example_trend_report.md").write_text(
            trend_to_markdown(trends[0]), encoding="utf-8"
        )
