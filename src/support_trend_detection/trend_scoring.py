"""Trend scoring and ranking."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from support_trend_detection.models import Trend

FRIENDLY_TITLES = {
    "api": "API rate-limit confusion",
    "billing": "Billing invoice requests",
    "bulk actions": "Bulk action requests",
    "csv": "CSV exports timing out for large datasets",
    "permissions": "Permissions confusion",
    "search": "Search performance degradation",
    "slack": "Slack integration disconnects",
    "sso": "SSO login failures",
}


def period_windows(
    tickets: pd.DataFrame,
    current_days: int,
    previous_days: int,
    reference_date: pd.Timestamp | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    ref = reference_date or tickets["created_at"].max()
    current_start = ref - pd.Timedelta(days=current_days - 1)
    previous_start = current_start - pd.Timedelta(days=previous_days)
    return previous_start.normalize(), current_start.normalize(), ref.normalize()


def growth_rate(current_volume: int, previous_volume: int) -> float:
    if previous_volume == 0:
        return float(current_volume) if current_volume else 0.0
    return (current_volume - previous_volume) / previous_volume


def classify_trend(current_volume: int, previous_volume: int, growth: float) -> str:
    if current_volume >= 20 and growth >= 1.0:
        return "Emerging product issue"
    if current_volume >= 12 and growth >= 0.5:
        return "Growing support friction"
    if current_volume >= 8 and previous_volume == 0:
        return "Newly visible theme"
    return "Watchlist pattern"


def priority_for_trend(current_volume: int, growth: float, enterprise_ticket_count: int) -> str:
    if enterprise_ticket_count >= 10 and current_volume >= 20 and growth >= 0.75:
        return "P1"
    if current_volume >= 15 and growth >= 0.5:
        return "P2"
    if current_volume >= 8:
        return "P3"
    return "P4"


def confidence_for_trend(current_volume: int, previous_volume: int, growth: float) -> tuple[str, str]:
    if current_volume >= 20 and growth >= 0.75:
        return "High", "High volume and strong period-over-period growth."
    if current_volume >= 10 and growth >= 0.25:
        return "Medium", "Moderate volume with a visible upward trend."
    return "Low", "Limited volume or weak growth; review manually before escalation."


def score_trends(
    tickets: pd.DataFrame,
    top_terms: dict[str, list[str]],
    current_days: int,
    previous_days: int,
    max_trends: int,
    reference_date: pd.Timestamp | None = None,
) -> list[Trend]:
    previous_start, current_start, ref = period_windows(
        tickets, current_days, previous_days, reference_date
    )
    current_mask = (tickets["created_at"] >= current_start) & (tickets["created_at"] <= ref)
    previous_mask = (tickets["created_at"] >= previous_start) & (tickets["created_at"] < current_start)

    trends: list[Trend] = []
    for cluster_id, group in tickets.groupby("cluster_id"):
        current_group = group[current_mask.loc[group.index]]
        previous_group = group[previous_mask.loc[group.index]]
        current_volume = len(current_group)
        previous_volume = len(previous_group)
        if current_volume < 4:
            continue

        growth = growth_rate(current_volume, previous_volume)
        terms = top_terms.get(cluster_id, [])
        product_areas = sorted(current_group["product_area"].value_counts().head(3).index.tolist())
        tiers = Counter(current_group["customer_tier"])
        enterprise_count = int(tiers.get("enterprise", 0))
        priority = priority_for_trend(current_volume, growth, enterprise_count)
        confidence, confidence_reason = confidence_for_trend(
            current_volume, previous_volume, growth
        )
        title = title_for_group(current_group, terms)
        supporting_ids = current_group.sort_values("created_at", ascending=False)[
            "ticket_id"
        ].head(8).tolist()

        trends.append(
            Trend(
                trend_id=str(cluster_id),
                title=title,
                classification=classify_trend(current_volume, previous_volume, growth),
                current_volume=current_volume,
                previous_volume=previous_volume,
                growth_rate=growth,
                product_areas=product_areas,
                customer_tiers=dict(sorted(tiers.items())),
                enterprise_ticket_count=enterprise_count,
                priority=priority,
                confidence=confidence,
                confidence_reason=confidence_reason,
                summary=summary_for_trend(title, current_volume, previous_volume, growth),
                customer_impact=impact_for_trend(current_group, title),
                recommended_action=recommended_action(priority, title),
                supporting_ticket_ids=supporting_ids,
                top_terms=terms,
            )
        )

    return sorted(
        trends,
        key=lambda trend: (
            priority_rank(trend.priority),
            trend.current_volume,
            trend.growth_rate,
            trend.enterprise_ticket_count,
        ),
        reverse=True,
    )[:max_trends]


def title_for_group(group: pd.DataFrame, terms: list[str]) -> str:
    tag_counts = Counter()
    for raw_tags in group["tags"]:
        for tag in str(raw_tags).split("|"):
            tag = tag.strip().replace("-", " ")
            if tag:
                tag_counts[tag] += 1
    if tag_counts:
        tag = tag_counts.most_common(1)[0][0]
        return FRIENDLY_TITLES.get(tag, tag.title())
    if terms:
        return terms[0].title()
    return "Recurring Support Theme"


def summary_for_trend(title: str, current: int, previous: int, growth: float) -> str:
    growth_pct = round(growth * 100)
    return (
        f"{title} appeared in {current} current-period tickets versus {previous} "
        f"in the prior period ({growth_pct}% growth)."
    )


def impact_for_trend(group: pd.DataFrame, title: str) -> str:
    top_area = group["product_area"].mode().iloc[0]
    enterprise_count = int((group["customer_tier"] == "enterprise").sum())
    return (
        f"Customers are reporting recurring {title.lower()} friction in {top_area}. "
        f"{enterprise_count} current-period tickets came from enterprise-tier accounts."
    )


def recommended_action(priority: str, title: str) -> str:
    if priority in {"P1", "P2"}:
        return (
            f"Open a Product/Engineering investigation for {title.lower()} and review "
            "the supporting tickets before assigning operational priority."
        )
    return (
        f"Keep {title.lower()} on the Support Operations watchlist and review again "
        "after the next analysis window."
    )


def priority_rank(priority: str) -> int:
    return {"P1": 4, "P2": 3, "P3": 2, "P4": 1}.get(priority, 0)
