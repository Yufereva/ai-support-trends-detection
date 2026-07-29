"""Trend Detection Dashboard backed by similarity and impact analysis."""

from __future__ import annotations

import html
import json
import sqlite3
from collections import Counter
from datetime import datetime
from textwrap import dedent

import streamlit as st

from escalation_quality_bridge import quality_panel_html, score_draft
from impact import calculate_customer_impact
from similarity import (
    DB_PATH,
    SIMILARITY_THRESHOLD,
    TREND_MIN_COUNT,
    TREND_WINDOW_DAYS,
    compute_embeddings,
    detect_trend,
    format_engineering_ticket_text,
    generate_engineering_ticket,
    score_similar_tickets,
)
from trend_review_store import load_confirmed_review, save_confirmed_review

TREND_CSS = """
<style>
    [data-testid="stAppViewContainer"] { background: #F8F9F9; }
    [data-testid="stMainBlockContainer"], .stMainBlockContainer {
        box-sizing: border-box; width: 100% !important; max-width: 1244px !important;
        margin: 0 auto; padding: 24px 32px 48px !important; overflow-x: hidden;
    }

    .trend-shell {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        box-sizing: border-box; color: #2f3941; width: 100%; min-width: 0; max-width: 100%;
        margin: 0; padding: 0; overflow-x: hidden;
    }
    .trend-topbar {
        display: flex; align-items: center; gap: 16px; margin-bottom: 18px;
        padding-bottom: 16px; border-bottom: 1px solid #d8dcde;
    }
    .trend-topbar h1 { font-size: 22px; margin: 0; font-weight: 600; }
    .trend-topbar .sub { color: #68737d; font-size: 13px; margin: 4px 0 0; }
    .trend-back {
        color: #1f73b7; text-decoration: none; font-size: 13px; white-space: nowrap;
    }
    .trend-back:hover { text-decoration: underline; }
    .trend-badge {
        display: inline-block; padding: 4px 10px; border-radius: 3px; font-size: 12px;
        font-weight: 600; margin-bottom: 12px;
    }
    .trend-badge.hot { background: #fff8e6; border: 1px solid #f5a623; color: #703b15; }
    .trend-badge.calm { background: #edf7ed; border: 1px solid #aecf9b; color: #186146; }
    .trend-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px;
    }
    @media (max-width: 850px) { .trend-grid { grid-template-columns: 1fr; } }
    .trend-card {
        background: #fff; border: 1px solid #d8dcde; border-radius: 4px; padding: 16px 18px;
    }
    .trend-card h2 {
        font-size: 12px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #68737d; margin: 0 0 12px;
    }
    .trend-card.full { grid-column: 1 / -1; }
    .trend-metric-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .trend-metric {
        background: #f8f9f9; border: 1px solid #e5e7e9; border-radius: 4px; padding: 10px;
    }
    .trend-metric .value { font-size: 22px; font-weight: 650; color: #17494d; }
    .trend-metric .label { font-size: 12px; color: #68737d; margin-top: 2px; }
    .trend-summary-title { font-size: 16px; font-weight: 600; margin: 0 0 8px; }
    .trend-summary-text { color: #49545c; font-size: 13px; line-height: 1.5; margin: 0; }
    .trend-tier-list, .trend-account-list, .trend-evidence-list { display: grid; gap: 8px; }
    .trend-tier-row, .trend-account-row, .trend-evidence-row {
        display: flex; justify-content: space-between; gap: 12px; align-items: flex-start;
        border-top: 1px solid #edf0f2; padding-top: 8px; font-size: 13px;
    }
    .trend-tier-row:first-child, .trend-account-row:first-child, .trend-evidence-row:first-child {
        border-top: none; padding-top: 0;
    }
    .trend-muted { color: #68737d; font-size: 12px; }
    .trend-strong { font-weight: 600; }
    .trend-timeline {
        display: flex; align-items: end; gap: 6px; height: 110px; padding-top: 8px;
        border-bottom: 1px solid #d8dcde;
    }
    .trend-bar-wrap {
        flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: end;
        min-width: 0; height: 100%;
    }
    .trend-bar { width: 100%; max-width: 44px; background: #1f73b7; border-radius: 3px 3px 0 0; }
    .trend-bar-label {
        color: #68737d; font-size: 10px; margin-top: 5px; white-space: nowrap;
    }
    .trend-evidence-row a { color: #1f73b7; text-decoration: none; font-weight: 600; }
    .trend-evidence-row a:hover { text-decoration: underline; }
    .trend-score {
        color: #17494d; background: #e7f4f5; border: 1px solid #b6d6d9; border-radius: 3px;
        font-size: 12px; padding: 2px 6px; white-space: nowrap;
    }
    .trend-draft {
        background: #f8f9f9; border: 1px solid #d8dcde; border-radius: 4px;
        padding: 12px; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 12px; line-height: 1.45; max-height: 360px; overflow: auto;
    }
    .trend-actions { display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap; }
    .trend-btn {
        display: inline-block; padding: 8px 16px; border-radius: 4px;
        font-size: 13px; font-weight: 500; text-decoration: none;
    }
    .trend-btn-primary,
    .trend-btn-primary:link,
    .trend-btn-primary:visited,
    .trend-btn-primary:hover,
    .trend-btn-primary:focus {
        background: #03363d; color: #fff !important; border: 1px solid #03363d;
    }
    .trend-btn-primary:hover,
    .trend-btn-primary:focus { background: #17494d; border-color: #17494d; }
    .trend-btn-secondary { background: #fff; color: #2f3941 !important; border: 1px solid #d8dcde; }
    .trend-btn-secondary:hover { background: #f8f9f9; }
    [class*="st-key-trend_confirm_"] button {
        width: auto !important; min-height: 46px; padding: 0 18px !important;
        white-space: nowrap;
    }
    .trend-empty {
        background: #fff; border: 1px solid #d8dcde; border-radius: 4px; padding: 18px;
        color: #49545c; font-size: 13px; line-height: 1.5;
    }
    .trend-investigation-title {
        font-size: 15px; font-weight: 600; color: #2f3941; margin: 6px 0 2px;
    }
    .trend-investigation-note { color: #68737d; font-size: 12px; margin-bottom: 10px; }
    .trend-table-head {
        color: #68737d; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .trend-table-data-grid {
        display: grid; grid-template-columns: minmax(300px, 3fr) 0.6fr 0.6fr 0.6fr;
        gap: 12px; align-items: start; width: 100%;
    }
    .trend-table-header { padding-bottom: 7px; }
    .trend-investigation-note, .trend-table-data-grid, .trend-table-cell {
        box-sizing: border-box; min-width: 0; max-width: 100%; overflow-wrap: anywhere;
    }
    .trend-table-cell { color: #2f3941; font-size: 13px; line-height: 1.4; }
    .trend-table-cell a { color: #1f73b7; font-weight: 600; text-decoration: none; }
    .trend-table-cell a:hover { text-decoration: underline; }
    .trend-table-cell.reason { color: #68737d; font-size: 11px; }
    @media (max-width: 1100px) {
        [data-testid="stMainBlockContainer"], .stMainBlockContainer { padding: 16px !important; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="column"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important;
        }
        .trend-topbar { align-items: flex-start; flex-wrap: wrap; }
        .trend-back { width: 100%; }
        .trend-table-header { display: none; }
        .trend-table-data-grid { grid-template-columns: 1fr 1fr; gap: 8px 12px; }
        .trend-table-cell.subject { grid-column: 1 / -1; }
        .trend-table-cell::before {
            content: attr(data-label); display: block; color: #68737d; font-size: 10px;
            font-weight: 600; text-transform: uppercase; margin-bottom: 2px;
        }
    }
    @media (max-width: 520px) {
        .trend-table-data-grid { grid-template-columns: 1fr; }
        .trend-table-cell.subject { grid-column: auto; }
        .trend-metric-row { grid-template-columns: 1fr; }
        .trend-event { grid-template-columns: 78px 12px 1fr; gap: 7px; }
    }
    .trend-event-list { display: grid; gap: 0; margin-top: 14px; }
    .trend-event {
        display: grid; grid-template-columns: 94px 12px 1fr; gap: 10px;
        min-height: 48px; font-size: 13px;
    }
    .trend-event-time { color: #68737d; font-size: 11px; padding-top: 1px; }
    .trend-event-marker { position: relative; width: 12px; }
    .trend-event-marker::before {
        content: ""; position: absolute; left: 5px; top: 5px; bottom: -5px;
        width: 1px; background: #d8dcde;
    }
    .trend-event:last-child .trend-event-marker::before { display: none; }
    .trend-event-marker::after {
        content: ""; position: absolute; left: 1px; top: 2px; width: 9px; height: 9px;
        border-radius: 50%; background: #1f73b7; border: 2px solid #fff;
        box-shadow: 0 0 0 1px #1f73b7;
    }
    .trend-event.synthetic .trend-event-marker::after { background: #6554c0; box-shadow: 0 0 0 1px #6554c0; }
    .trend-event.confirmed .trend-event-marker::after { background: #038153; box-shadow: 0 0 0 1px #038153; }
    .trend-event-detail { color: #68737d; font-size: 11px; margin-top: 2px; }
</style>
"""


@st.cache_resource(show_spinner="Loading embeddings for trend dashboard...")
def _get_cache() -> dict:
    return compute_embeddings()


@st.cache_data
def _get_ticket(ticket_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, created_at, subject, body, category, priority, status, "
        "customer_tier, tags, cluster, requester_email, account_id "
        "FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


@st.cache_data
def _get_ticket_index(ticket_ids: tuple[str, ...]) -> dict[str, dict]:
    if not ticket_ids:
        return {}
    placeholders = ",".join("?" for _ in ticket_ids)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT id, created_at, subject, category, priority, status, "
        f"customer_tier, tags, account_id "
        f"FROM tickets WHERE id IN ({placeholders})",
        ticket_ids,
    ).fetchall()
    conn.close()
    return {row["id"]: dict(row) for row in rows}


def trend_dashboard_url(ticket_id: str | None = None) -> str:
    if ticket_id:
        return f"?mode=trend&ticket={html.escape(ticket_id, quote=True)}"
    return "?mode=trend"


def _fmt_pct(value: float) -> str:
    return f"{value:.0%}"


def _fmt_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%b %d")
    except (AttributeError, ValueError):
        return value[:10] if value else "-"


def _clean_html(markup: str) -> str:
    return "\n".join(line.strip() for line in markup.splitlines() if line.strip())


def _parse_tags(value: str | list[str] | None) -> list[str]:
    if isinstance(value, list):
        return [str(tag) for tag in value]
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(tag) for tag in parsed] if isinstance(parsed, list) else []


def _similarity_explanation(trigger: dict, candidate: dict) -> str:
    reasons = []
    if candidate.get("category") == trigger.get("category"):
        reasons.append(f"same {str(candidate.get('category', '')).replace('_', ' ')} category")

    shared_tags = sorted(set(_parse_tags(trigger.get("tags"))) & set(_parse_tags(candidate.get("tags"))))
    if shared_tags:
        signals = ", ".join(tag.replace("-", " ").upper() for tag in shared_tags[:3])
        reasons.append(f"shared signals: {signals}")

    return "; ".join(reasons) or "semantic language match"


def _build_review_candidates(
    cache: dict,
    trend: dict,
    ticket_index: dict[str, dict],
    trigger: dict,
) -> list[dict]:
    scores = score_similar_tickets(cache, trigger["id"], trend["similar_ids"])
    candidates = []
    for candidate_id in trend["similar_ids"]:
        ticket = ticket_index.get(candidate_id)
        if not ticket:
            continue
        candidates.append(
            {
                **ticket,
                "similarity": scores.get(candidate_id, 0.0),
                "explanation": _similarity_explanation(trigger, ticket),
            }
        )
    return sorted(candidates, key=lambda item: item["similarity"], reverse=True)


def _reviewed_trend(trend: dict, included_ids: list[str]) -> dict:
    reviewed = dict(trend)
    reviewed["similar_ids"] = list(included_ids)
    reviewed["similar_count"] = len(included_ids)
    reviewed["is_potential_trend"] = len(included_ids) >= trend.get("min_count", TREND_MIN_COUNT)
    return reviewed


def _build_timeline(ticket_index: dict[str, dict]) -> str:
    dated = []
    for ticket in ticket_index.values():
        try:
            dated.append(datetime.fromisoformat(ticket.get("created_at", "").replace("Z", "+00:00")))
        except (AttributeError, ValueError):
            continue

    if not dated:
        return '<div class="trend-muted">No dated tickets in this cluster.</div>'

    hourly = max(dated) - min(dated)
    use_hours = hourly.days < 2
    bucket_format = "%Y-%m-%dT%H" if use_hours else "%Y-%m-%d"
    label_format = "%H:00" if use_hours else "%b %d"
    buckets = Counter(created.strftime(bucket_format) for created in dated)

    if not buckets:
        return '<div class="trend-muted">No dated tickets in this cluster.</div>'

    bucket_keys = sorted(buckets)[-12:]
    max_count = max(buckets[key] for key in bucket_keys) or 1
    bars = []
    for bucket in bucket_keys:
        height = max(8, round((buckets[bucket] / max_count) * 86))
        label = datetime.strptime(bucket, bucket_format).strftime(label_format)
        bars.append(
            f'<div class="trend-bar-wrap" title="{html.escape(bucket)}: {buckets[bucket]} tickets">'
            f'<div class="trend-bar" style="height:{height}px;"></div>'
            f'<div class="trend-bar-label">{html.escape(label)}</div></div>'
        )
    return f'<div class="trend-timeline">{"".join(bars)}</div>'


OPERATIONAL_EVENT_LABELS = {
    "identity": "SCIM authorization worker release",
    "api": "API gateway release",
    "billing": "Billing rules deployment",
    "notifications": "Notification worker deployment",
}


def _build_operational_events(
    ticket_index: dict[str, dict],
    category: str,
    trigger_ticket_id: str,
    confirmed: bool,
) -> str:
    dated_tickets = []
    for ticket in ticket_index.values():
        try:
            created = datetime.fromisoformat(ticket.get("created_at", "").replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        dated_tickets.append((created, ticket))
    dated_tickets.sort(key=lambda item: item[0])
    if not dated_tickets:
        return '<div class="trend-muted">No operational events available.</div>'

    first_at, first_ticket = dated_tickets[0]
    trigger_at, trigger_ticket = next(
        ((created, ticket) for created, ticket in dated_tickets if ticket["id"] == trigger_ticket_id),
        dated_tickets[-1],
    )
    span = max(trigger_at - first_at, datetime.resolution)
    operation_at = first_at + span * 0.3
    threshold_at, threshold_ticket = dated_tickets[min(TREND_MIN_COUNT, len(dated_tickets) - 1)]
    operation_name = OPERATIONAL_EVENT_LABELS.get(category, "Service deployment")

    events = [
        (
            first_at,
            "First matching support report",
            f'{first_ticket["id"]} - {first_ticket["subject"]}',
            "",
        ),
        (
            operation_at,
            operation_name,
            "Synthetic operational marker for investigation correlation; not evidence of causation.",
            "synthetic",
        ),
        (
            threshold_at,
            "Trend threshold reached",
            f'{threshold_ticket["id"]} supplied the required earlier-match volume.',
            "",
        ),
        (
            trigger_at,
            "Trigger ticket analyzed",
            f'{trigger_ticket["id"]} opened the current investigation.',
            "",
        ),
    ]
    if confirmed:
        events.append(
            (
                None,
                "Support review confirmed",
                "Reviewed ticket set and recalculated impact saved to the Jira draft.",
                "confirmed",
            )
        )

    rows = []
    for created, title, detail, css_class in events:
        time_label = created.strftime("%b %d %H:%M") if created else "Review"
        rows.append(
            f'<div class="trend-event {css_class}">'
            f'<div class="trend-event-time">{html.escape(time_label)}</div>'
            '<div class="trend-event-marker"></div>'
            f'<div><span class="trend-strong">{html.escape(title)}</span>'
            f'<div class="trend-event-detail">{html.escape(detail)}</div></div></div>'
        )
    return f'<div class="trend-event-list">{"".join(rows)}</div>'


def _include_key(trigger_ticket_id: str, candidate_id: str) -> str:
    return f"trend_include_{trigger_ticket_id}_{candidate_id}"


def _render_investigation_table(
    trigger_ticket_id: str,
    candidates: list[dict],
    threshold: float,
    default_included_ids: set[str] | None = None,
) -> list[str]:
    for candidate in candidates:
        key = _include_key(trigger_ticket_id, candidate["id"])
        if key not in st.session_state:
            st.session_state[key] = (
                True if default_included_ids is None else candidate["id"] in default_included_ids
            )

    st.markdown(
        '<div class="trend-investigation-title">Investigation table</div>'
        '<div class="trend-investigation-note">'
        'Embedding score measures semantic similarity. Match reasons summarize shared metadata '
        'and do not prove a common root cause.'
        '</div>',
        unsafe_allow_html=True,
    )

    filter_search, filter_review = st.columns([2, 1])
    with filter_search:
        search = st.text_input(
            "Search cluster",
            key=f"trend_search_{trigger_ticket_id}",
            placeholder="Ticket ID or subject",
        ).strip().lower()
    with filter_review:
        review_filter = st.selectbox(
            "Review state",
            ["All", "Included", "Excluded"],
            key=f"trend_review_filter_{trigger_ticket_id}",
        )
    filter_status, filter_tier = st.columns(2)
    with filter_status:
        statuses = sorted({str(candidate.get("status", "")).title() for candidate in candidates})
        selected_statuses = st.multiselect(
            "Status",
            statuses,
            key=f"trend_status_{trigger_ticket_id}",
        )
    with filter_tier:
        tiers = sorted({str(candidate.get("customer_tier", "")).title() for candidate in candidates})
        selected_tiers = st.multiselect(
            "Account tier",
            tiers,
            key=f"trend_tier_{trigger_ticket_id}",
        )
    min_score = st.slider(
        "Minimum similarity",
        min_value=int(threshold * 100),
        max_value=100,
        value=int(threshold * 100),
        key=f"trend_min_score_{trigger_ticket_id}",
        format="%d%%",
    )

    visible = []
    for candidate in candidates:
        included = bool(st.session_state[_include_key(trigger_ticket_id, candidate["id"])])
        haystack = f'{candidate["id"]} {candidate["subject"]}'.lower()
        if search and search not in haystack:
            continue
        if selected_statuses and str(candidate.get("status", "")).title() not in selected_statuses:
            continue
        if selected_tiers and str(candidate.get("customer_tier", "")).title() not in selected_tiers:
            continue
        if candidate["similarity"] * 100 < min_score:
            continue
        if review_filter == "Included" and not included:
            continue
        if review_filter == "Excluded" and included:
            continue
        visible.append(candidate)

    header = st.columns([0.08, 0.92])
    header[0].markdown('<div class="trend-table-head">Include</div>', unsafe_allow_html=True)
    header[1].markdown(
        '<div class="trend-table-data-grid trend-table-header">'
        '<div class="trend-table-head">Ticket</div>'
        '<div class="trend-table-head">Created</div>'
        '<div class="trend-table-head">Status</div>'
        '<div class="trend-table-head">Tier</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    for candidate in visible:
        row = st.columns([0.08, 0.92])
        row[0].checkbox(
            f'Include {candidate["id"]}',
            key=_include_key(trigger_ticket_id, candidate["id"]),
            label_visibility="collapsed",
        )
        ticket_href = f'?ticket={html.escape(candidate["id"], quote=True)}&mode=detail'
        row[1].markdown(
            '<div class="trend-table-data-grid">'
            f'<div class="trend-table-cell subject" data-label="Ticket">'
            f'<a href="{ticket_href}">{html.escape(candidate["id"])}</a> '
            f'<span class="trend-score">{html.escape(_fmt_pct(candidate["similarity"]))}</span><br>'
            f'{html.escape(candidate["subject"])}'
            f'<div class="trend-table-cell reason" style="margin-top:3px;">'
            f'Why: {html.escape(candidate["explanation"])}</div></div>'
            f'<div class="trend-table-cell" data-label="Created">'
            f'{html.escape(_fmt_date(candidate.get("created_at", "")))}</div>'
            f'<div class="trend-table-cell" data-label="Status">'
            f'{html.escape(str(candidate.get("status", "")).title())}</div>'
            f'<div class="trend-table-cell" data-label="Tier">'
            f'{html.escape(str(candidate.get("customer_tier", "")).title())}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()

    if not visible:
        st.info("No cluster tickets match the current filters.")

    included_ids = [
        candidate["id"]
        for candidate in candidates
        if st.session_state[_include_key(trigger_ticket_id, candidate["id"])]
    ]
    st.caption(
        f"{len(visible)} shown | {len(included_ids)} included | "
        f"{len(candidates) - len(included_ids)} excluded"
    )
    return included_ids


def _tier_rows(impact: dict) -> str:
    rows = []
    for tier in ("enterprise", "pro", "free"):
        count = impact["by_tier"].get(tier, 0)
        arr = impact["arr_by_tier"].get(tier, 0)
        if not count and not arr:
            continue
        rows.append(
            f'<div class="trend-tier-row">'
            f'<span><span class="trend-strong">{tier.title()}</span> accounts</span>'
            f'<span>{count} - ${arr:,.0f} ARR</span></div>'
        )
    return "".join(rows) or '<div class="trend-muted">No linked account impact.</div>'


def _account_rows(impact: dict) -> str:
    rows = []
    for account in impact.get("top_accounts", [])[:5]:
        rows.append(
            f'<div class="trend-account-row">'
            f'<span><span class="trend-strong">{html.escape(account["name"])}</span>'
            f'<br><span class="trend-muted">{html.escape(account["tier"].title())}</span></span>'
            f'<span>{html.escape(account["arr_formatted"])}</span></div>'
        )
    return "".join(rows) or '<div class="trend-muted">No Salesforce accounts linked.</div>'


def _evidence_rows(similar: list[dict], ticket_index: dict[str, dict]) -> str:
    rows = []
    for item in similar:
        ticket = ticket_index.get(item["id"], {})
        status = ticket.get("status", "")
        created = ticket.get("created_at", item.get("created_at", ""))
        rows.append(
            f'<div class="trend-evidence-row">'
            f'<span><a href="?ticket={html.escape(item["id"], quote=True)}&mode=detail">'
            f'{html.escape(item["id"])}</a> '
            f'{html.escape(item["subject"])}</span>'
            f'<span class="trend-score">{_fmt_pct(item["similarity"])}</span>'
            f'<span class="trend-muted">{html.escape(item["category"])} - '
            f'{html.escape(status)} - {_fmt_date(created)}</span></div>'
        )
    return "".join(rows) or '<div class="trend-muted">No similar tickets found.</div>'


def _render_missing_ticket(ticket_id: str | None):
    ticket_text = html.escape(ticket_id or "No ticket selected")
    st.markdown(
        _clean_html(dedent(f"""
        <div class="trend-shell">
            <div class="trend-topbar">
                <div style="flex:1;">
                    <h1>Trend Detection Dashboard</h1>
                    <div class="sub">Cluster view - similar tickets, ARR, timeline, evidence</div>
                </div>
                <a class="trend-back" href="?mode=list">Back to Zendesk</a>
            </div>
            <div class="trend-empty">
                Could not load <strong>{ticket_text}</strong>. Open a Zendesk ticket first, then use
                the Analytics icon or a URL like <code>?mode=trend&amp;ticket=T-0004</code>.
            </div>
        </div>
        """)),
        unsafe_allow_html=True,
    )


def render_trend_dashboard(ticket_id: str | None = None):
    st.markdown(TREND_CSS, unsafe_allow_html=True)

    if not ticket_id:
        _render_missing_ticket(ticket_id)
        return

    ticket = _get_ticket(ticket_id)
    if not ticket:
        _render_missing_ticket(ticket_id)
        return

    cache = _get_cache()
    detected_trend = detect_trend(cache, ticket_id)
    cluster_ids = tuple(dict.fromkeys([ticket_id, *detected_trend["similar_ids"]]))
    full_ticket_index = _get_ticket_index(cluster_ids)
    candidates = _build_review_candidates(cache, detected_trend, full_ticket_index, ticket)
    threshold = detected_trend.get("threshold", SIMILARITY_THRESHOLD)
    back_href = f"?ticket={html.escape(ticket_id, quote=True)}&mode=detail"

    st.markdown(
        _clean_html(dedent(f"""
        <div class="trend-shell">
            <div class="trend-topbar">
                <div style="flex:1;">
                    <h1>Trend Detection Dashboard</h1>
                    <div class="sub">Investigation workspace - evidence review, impact, and escalation</div>
                    <div class="sub">Trigger ticket: <strong>{html.escape(ticket_id)}</strong></div>
                </div>
                <a class="trend-back" href="{back_href}">Back to Zendesk</a>
            </div>
        </div>
        """)),
        unsafe_allow_html=True,
    )

    confirmation_key = f"reviewed_trend_{ticket_id}"
    persisted_review = load_confirmed_review(ticket_id)
    if confirmation_key not in st.session_state and persisted_review:
        st.session_state[confirmation_key] = persisted_review
    default_included_ids = None
    if persisted_review:
        default_included_ids = set(persisted_review.get("trend", {}).get("similar_ids", []))

    included_ids = _render_investigation_table(
        ticket_id,
        candidates,
        threshold,
        default_included_ids,
    )
    reviewed_trend = _reviewed_trend(detected_trend, included_ids)
    included_candidates = [candidate for candidate in candidates if candidate["id"] in included_ids]
    impact = calculate_customer_impact(included_ids, ticket_id)
    draft = generate_engineering_ticket(
        cache,
        ticket_id,
        reviewed_trend,
        included_candidates,
        impact,
    )
    draft_text = format_engineering_ticket_text(draft)

    review_signature = tuple(sorted(included_ids))
    confirmed_review = st.session_state.get(confirmation_key)
    is_confirmed = bool(
        confirmed_review
        and tuple(confirmed_review.get("included_signature", ())) == review_signature
    )
    trend_class = "hot" if reviewed_trend["is_potential_trend"] else "calm"
    trend_label = (
        "Reviewed cluster meets trend threshold"
        if reviewed_trend["is_potential_trend"]
        else "Reviewed cluster is below trend threshold"
    )
    cluster_label = html.escape(reviewed_trend["category"].replace("_", " ").title())
    subject = html.escape(reviewed_trend["subject"])
    reviewed_ticket_index = {
        item_id: full_ticket_index[item_id]
        for item_id in [ticket_id, *included_ids]
        if item_id in full_ticket_index
    }
    excluded_count = len(candidates) - len(included_ids)

    st.markdown(
        _clean_html(dedent(f"""
        <div class="trend-shell" style="padding-top:18px;">
            <div class="trend-badge {trend_class}">{trend_label}</div>

            <div class="trend-grid">
                <div class="trend-card full">
                    <h2>Cluster summary</h2>
                    <div class="trend-summary-title">{cluster_label}: {subject}</div>
                    <p class="trend-summary-text">
                        {reviewed_trend["similar_count"]} reviewed earlier tickets remain in the cluster;
                        {excluded_count} {"ticket" if excluded_count == 1 else "tickets"} excluded.
                        Impact and the Jira draft below use only the reviewed ticket set.
                    </p>
                    <div class="trend-metric-row" style="margin-top:12px;">
                        <div class="trend-metric">
                            <div class="value">{reviewed_trend["similar_count"]}</div>
                            <div class="label">Included similar tickets</div>
                        </div>
                        <div class="trend-metric">
                            <div class="value">{excluded_count}</div>
                            <div class="label">Excluded from review</div>
                        </div>
                        <div class="trend-metric">
                            <div class="value">{_fmt_pct(threshold)}</div>
                            <div class="label">Similarity cutoff</div>
                        </div>
                        <div class="trend-metric">
                            <div class="value">{TREND_WINDOW_DAYS}d</div>
                            <div class="label">Detection window</div>
                        </div>
                    </div>
                </div>

                <div class="trend-card">
                    <h2>Customer impact (Salesforce)</h2>
                    <div class="trend-metric-row">
                        <div class="trend-metric">
                            <div class="value">{impact["unique_accounts"]}</div>
                            <div class="label">Unique accounts</div>
                        </div>
                        <div class="trend-metric">
                            <div class="value">{impact["by_tier"].get("enterprise", 0)}</div>
                            <div class="label">Enterprise</div>
                        </div>
                        <div class="trend-metric">
                            <div class="value">{html.escape(impact["arr_at_risk_formatted"])}</div>
                            <div class="label">ARR at risk</div>
                        </div>
                    </div>
                    <div class="trend-tier-list" style="margin-top:12px;">{_tier_rows(impact)}</div>
                </div>

                <div class="trend-card">
                    <h2>Top accounts</h2>
                    <div class="trend-account-list">{_account_rows(impact)}</div>
                </div>

                <div class="trend-card">
                    <h2>Ticket volume</h2>
                    {_build_timeline(reviewed_ticket_index)}
                    <div class="trend-muted" style="margin-top:8px;">
                        Included cluster tickets grouped by hour or day.
                    </div>
                </div>

                <div class="trend-card">
                    <h2>Operational timeline</h2>
                    {_build_operational_events(
                        reviewed_ticket_index,
                        reviewed_trend["category"],
                        ticket_id,
                        is_confirmed,
                    )}
                </div>

                <div class="trend-card full">
                    <h2>Reviewed evidence</h2>
                    <div class="trend-evidence-list">
                        {_evidence_rows(included_candidates, reviewed_ticket_index)}
                    </div>
                </div>

                <div class="trend-card full">
                    <h2>Reviewed engineering ticket draft</h2>
                    <div class="trend-draft">{html.escape(draft_text)}</div>
                </div>
            </div>
        </div>
        """)),
        unsafe_allow_html=True,
    )

    quality_report = score_draft(draft)
    st.markdown(
        _clean_html(
            dedent(
                f"""
                <div class="trend-shell" style="padding-top:12px;padding-bottom:8px;">
                    <div class="trend-card full" style="margin:0;">
                        <h2>Escalation Quality (before Create in Jira)</h2>
                        {quality_panel_html(quality_report)}
                    </div>
                </div>
                """
            )
        ),
        unsafe_allow_html=True,
    )

    confirm_col, status_col = st.columns(
        [0.32, 0.68],
        gap="medium",
        vertical_alignment="center",
    )
    with confirm_col:
        confirmed_now = st.button(
            "Confirm trend and create Jira ticket",
            type="primary",
            disabled=not reviewed_trend["is_potential_trend"],
            use_container_width=False,
            key=f"trend_confirm_{ticket_id}",
        )
    if confirmed_now:
        linked_support_tickets = [
            {
                "id": ticket_id,
                "subject": ticket["subject"],
                "relationship": "Trigger",
            },
            *[
                {
                    "id": candidate["id"],
                    "subject": candidate["subject"],
                    "relationship": "Similar",
                }
                for candidate in included_candidates
            ],
        ]
        reviewed_analysis = {
            "trend": reviewed_trend,
            "impact": impact,
            "draft": draft,
            "linked_support_tickets": linked_support_tickets,
            "included_signature": review_signature,
        }
        st.session_state[confirmation_key] = reviewed_analysis
        save_confirmed_review(ticket_id, reviewed_analysis)

        api_key = f"api_results_{ticket_id}"
        api_analysis = dict(st.session_state.get(api_key) or {})
        api_analysis.update(
            {
                "ticket_id": ticket_id,
                "trigger": ticket_id,
                "similar_tickets": included_candidates,
                "trend": reviewed_trend,
                "impact": impact,
                "engineering_draft": draft,
                "engineering_draft_text": draft_text,
                "analysis_source": "confirmed-review",
            }
        )
        st.session_state[api_key] = api_analysis

        # Jump straight into the Jira Create-issue draft with the just-confirmed data.
        st.session_state["_create_jira_requested"] = ticket_id
        st.session_state["_jira_create_return"] = {"mode": "trend", "ticket": ticket_id}
        st.rerun()

    with status_col:
        if is_confirmed:
            st.success(
                f"Confirmed: {len(included_ids)} similar tickets and "
                f"{impact['arr_at_risk_formatted']} ARR saved to the Jira draft."
            )
        elif reviewed_trend["is_potential_trend"]:
            if quality_report["verdict"] == "ready":
                st.warning("Review changes are not yet confirmed for Jira.")
            else:
                st.warning(
                    f"Escalation Quality: {quality_report['verdict']} "
                    f"({quality_report['score_pct']}%). "
                    "You can still confirm — enrich the draft or proceed with the caveat."
                )
        else:
            st.info(
                f"At least {reviewed_trend['min_count']} similar tickets are required to confirm a trend."
            )

    create_href = f"?mode=trend&ticket={html.escape(ticket_id, quote=True)}&create_jira=1"
    create_action = ""
    if is_confirmed:
        create_action = (
            f'<a class="trend-btn trend-btn-primary" href="{create_href}">'
            "Create or update Jira issue</a>"
        )
    st.markdown(
        f'<div class="trend-actions">{create_action}'
        '<a class="trend-btn trend-btn-secondary" href="?mode=jira">View Jira backlog</a>'
        "</div>",
        unsafe_allow_html=True,
    )
