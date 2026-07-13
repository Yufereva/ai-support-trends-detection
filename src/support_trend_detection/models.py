"""Data models for trend detection outputs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Trend:
    trend_id: str
    title: str
    classification: str
    current_volume: int
    previous_volume: int
    growth_rate: float
    product_areas: list[str]
    customer_tiers: dict[str, int]
    enterprise_ticket_count: int
    priority: str
    confidence: str
    confidence_reason: str
    summary: str
    customer_impact: str
    recommended_action: str
    supporting_ticket_ids: list[str] = field(default_factory=list)
    top_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trend_id": self.trend_id,
            "title": self.title,
            "classification": self.classification,
            "current_volume": self.current_volume,
            "previous_volume": self.previous_volume,
            "growth_rate": round(self.growth_rate, 3),
            "product_areas": self.product_areas,
            "customer_tiers": self.customer_tiers,
            "enterprise_ticket_count": self.enterprise_ticket_count,
            "priority": self.priority,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "summary": self.summary,
            "customer_impact": self.customer_impact,
            "recommended_action": self.recommended_action,
            "supporting_ticket_ids": self.supporting_ticket_ids,
            "top_terms": self.top_terms,
        }
