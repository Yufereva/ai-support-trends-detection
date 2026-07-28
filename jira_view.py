"""Jira-style engineering escalation view for Trend Detection demo."""

import html
import json
from datetime import date
from pathlib import Path

import streamlit as st

from impact import calculate_customer_impact
from similarity import (
    compute_embeddings,
    detect_trend,
    find_similar,
    generate_engineering_ticket,
)
from trend_review_store import load_confirmed_review

ROOT = Path(__file__).resolve().parent
JIRA_SEED_PATH = ROOT / "jira_issues.json"
JIRA_ISSUES_PATH = ROOT / "data" / "runtime" / "jira_issues.json"

PROJECT_NAME = "Escalation from support"
PROJECT_KEY = "ENG"

SVG_JIRA_LOGO = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">'
    '<path d="M11.5 2L2 12.5l9.5 9.5 9.5-9.5L11.5 2z" fill="#2684FF"/>'
    '<path d="M11.5 6.5L6 12l5.5 5.5L17 12l-5.5-5.5z" fill="#0052CC"/>'
    "</svg>"
)
SVG_BUG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="10" fill="#E5493A"/>'
    '<path d="M12 8v4M12 16h.01" stroke="#fff" stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)
SVG_TASK = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4BADE8" stroke-width="2">'
    '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>'
    "</svg>"
)
SVG_STORY = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none">'
    '<rect x="3" y="3" width="18" height="18" rx="2" fill="#63BA3C"/>'
    '<path d="M8 12h8M8 8h8M8 16h5" stroke="#fff" stroke-width="2"/>'
    "</svg>"
)
SVG_SEARCH = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/>'
    "</svg>"
)
SVG_CHEVRON = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    '<path d="M6 9l6 6 6-6"/>'
    "</svg>"
)
SVG_CHEVRON_RIGHT = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    '<path d="M9 6l6 6-6 6"/>'
    "</svg>"
)

JIRA_CSS = """
<style>
    body.jira-mode [data-testid="stAppViewContainer"],
    body.jira-detail-mode [data-testid="stAppViewContainer"] { background: #F4F5F7; }
    body.jira-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)),
    body.jira-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) {
        flex-wrap: nowrap !important; width: 100% !important;
    }
    body.jira-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="column"]:nth-child(1),
    body.jira-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="stColumn"]:nth-child(1),
    body.jira-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="column"]:nth-child(1),
    body.jira-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="stColumn"]:nth-child(1) {
        flex: 0 0 240px !important; width: 240px !important; min-width: 240px !important;
        max-width: 240px !important; background: #F4F5F7; border-right: 1px solid #DFE1E6;
        min-height: calc(100vh - 56px);
    }
    body.jira-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="column"]:nth-child(2),
    body.jira-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="stColumn"]:nth-child(2),
    body.jira-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="column"]:nth-child(2),
    body.jira-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-jira_search)) > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 0% !important; min-width: 0 !important;
        min-height: calc(100vh - 56px); overflow-x: auto !important;
        background: #fff;
    }

    [data-testid="element-container"]:has(.jira-topbar),
    [data-testid="stElementContainer"]:has(.jira-topbar) {
        min-height: 56px !important; overflow: visible !important;
        margin: 0 !important; padding: 0 !important;
    }
    .jira-topbar {
        display: flex; align-items: center; gap: 12px;
        background: #0747A6; color: #fff; padding: 0 12px; height: 56px;
        margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        position: relative; z-index: 2; flex-shrink: 0;
    }
    .jira-topbar-logo { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; white-space: nowrap; margin-right: 4px; }
    .jira-topbar-logo svg { flex-shrink: 0; }
    .jira-topbar-nav { display: flex; align-items: center; gap: 2px; }
    .jira-topbar-nav a {
        color: rgba(255,255,255,0.9); text-decoration: none; font-size: 14px;
        padding: 6px 10px; border-radius: 3px; white-space: nowrap;
    }
    .jira-topbar-nav a:hover { background: rgba(255,255,255,0.12); color: #fff; }
    .jira-topbar-search {
        flex: 1; max-width: 480px; display: flex; align-items: center; gap: 8px;
        background: rgba(255,255,255,0.15); border-radius: 3px; padding: 7px 12px;
        font-size: 14px; color: rgba(255,255,255,0.85); margin-left: 8px;
    }
    .jira-topbar-search svg { flex-shrink: 0; opacity: 0.85; }
    .jira-topbar-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; }
    .jira-create-btn {
        background: #0065FF; color: #fff; border: none; border-radius: 3px;
        padding: 6px 12px; font-size: 14px; font-weight: 500; cursor: default;
    }
    .jira-back-link {
        color: rgba(255,255,255,0.9); font-size: 13px; text-decoration: none;
        padding: 4px 8px; border-radius: 3px; white-space: nowrap;
    }
    .jira-back-link:hover { background: rgba(255,255,255,0.15); color: #fff; }

    .jira-sidebar {
        padding: 0 0 16px; font-size: 14px; color: #42526E;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    .jira-project-header {
        padding: 16px 16px 12px; border-bottom: 1px solid #DFE1E6; margin-bottom: 4px;
    }
    .jira-project-header-link {
        display: flex; align-items: flex-start; gap: 10px; text-decoration: none; color: inherit;
    }
    .jira-project-header-link:hover .jira-project-title { color: #0052CC; }
    .jira-project-icon {
        width: 32px; height: 32px; background: #0052CC; color: #fff;
        border-radius: 3px; display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 700; flex-shrink: 0;
    }
    .jira-project-title { font-size: 14px; font-weight: 600; color: #172B4D; line-height: 1.3; }
    .jira-project-type { font-size: 12px; color: #6B778C; margin-top: 2px; }
    .jira-nav-item {
        display: flex; align-items: center; gap: 10px; padding: 6px 16px 6px 20px;
        color: #42526E; text-decoration: none; font-size: 14px; line-height: 20px;
    }
    .jira-nav-item:hover { background: #EBECF0; color: #172B4D; }
    .jira-nav-item.active { background: #DEEBFF; color: #0052CC; font-weight: 500; }
    .jira-nav-icon { width: 16px; text-align: center; flex-shrink: 0; opacity: 0.75; font-size: 13px; }
    .jira-nav-item.active .jira-nav-icon { opacity: 1; }
    .jira-sidebar-divider { border-top: 1px solid #DFE1E6; margin: 8px 0; }
    .jira-filter-item {
        display: block; padding: 6px 16px 6px 36px; color: #42526E;
        text-decoration: none; font-size: 14px;
    }
    .jira-filter-item:hover { background: #EBECF0; color: #172B4D; }
    .jira-filter-item.active { background: #DEEBFF; color: #0052CC; font-weight: 500; }
    .jira-sidebar-section {
        padding: 8px 16px 4px; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.5px; color: #6B778C;
    }

    .jira-main { background: #fff; min-height: calc(100vh - 56px); }
    .jira-board-header {
        padding: 20px 24px 12px; border-bottom: 1px solid #DFE1E6;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }
    .jira-board-title { font-size: 20px; font-weight: 500; color: #172B4D; margin: 0; }
    .jira-board-actions { display: flex; gap: 8px; align-items: center; }
    .jira-btn-secondary {
        background: #FAFBFC; border: 1px solid #DFE1E6; border-radius: 3px;
        padding: 6px 12px; font-size: 14px; color: #42526E; cursor: default;
    }
    .jira-btn-primary {
        background: #0052CC; border: none; border-radius: 3px;
        padding: 6px 12px; font-size: 14px; color: #fff; font-weight: 500; cursor: default;
    }

    .jira-sprint {
        margin: 16px 24px; border: 1px solid #DFE1E6; border-radius: 3px; background: #FAFBFC;
    }
    .jira-sprint-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 12px; background: #fff; border-bottom: 1px solid #DFE1E6;
        border-radius: 3px 3px 0 0;
    }
    .jira-sprint-title { font-size: 14px; font-weight: 600; color: #172B4D; }
    .jira-sprint-meta { font-size: 13px; color: #6B778C; }
    .jira-sprint-actions { display: flex; gap: 8px; align-items: center; }

    .jira-issue-list { background: #fff; }
    .jira-issue-row {
        display: flex; align-items: center; gap: 8px; padding: 6px 12px;
        border-bottom: 1px solid #EBECF0; font-size: 14px; color: #172B4D;
        min-height: 40px;
    }
    .jira-issue-row:hover { background: #F4F5F7; }
    .jira-issue-row.jira-row-selected { background: #DEEBFF; }
    .jira-issue-type { flex-shrink: 0; display: flex; align-items: center; }
    .jira-key {
        color: #0052CC; font-weight: 500; text-decoration: none; white-space: nowrap;
        flex-shrink: 0; font-size: 13px;
    }
    .jira-key:hover { text-decoration: underline; }
    .jira-summary {
        flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .jira-row-pill { flex-shrink: 0; }
    .jira-row-avatar { flex-shrink: 0; margin-left: auto; }

    .jira-pill {
        display: inline-block; padding: 2px 6px; border-radius: 3px;
        font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px;
        white-space: nowrap;
    }
    .jira-pill-api { background: #DEEBFF; color: #0747A6; }
    .jira-pill-billing { background: #E3FCEF; color: #006644; }
    .jira-pill-mobile { background: #EAE6FF; color: #403294; }
    .jira-pill-sso { background: #EAE6FF; color: #403294; }
    .jira-pill-accounts { background: #EAE6FF; color: #403294; }
    .jira-pill-export { background: #FFF0B3; color: #974F0C; }
    .jira-pill-performance { background: #FFEBE6; color: #BF2600; }
    .jira-pill-integrations { background: #E6FCFF; color: #008DA6; }
    .jira-pill-database { background: #FFFAE6; color: #974F0C; }
    .jira-pill-feature-flags { background: #DFE1E6; color: #42526E; }
    .jira-pill-notifications { background: #E6FCFF; color: #008DA6; }
    .jira-pill-feedback { background: #FFEBE6; color: #BF2600; }
    .jira-pill-default { background: #DFE1E6; color: #42526E; }

    .jira-avatar {
        display: inline-flex; align-items: center; justify-content: center;
        width: 24px; height: 24px; border-radius: 50%; font-size: 10px; font-weight: 600;
        color: #fff; text-transform: uppercase;
    }
    .jira-avatar-unassigned {
        background: #DFE1E6; color: #97A0AF; font-size: 14px;
    }

    .jira-backlog-section {
        margin: 16px 24px 24px; border: 1px solid #DFE1E6; border-radius: 3px; background: #FAFBFC;
    }
    .jira-backlog-header {
        display: flex; align-items: center; gap: 8px; padding: 10px 12px;
        font-size: 14px; font-weight: 600; color: #172B4D; cursor: default;
    }
    .jira-backlog-count {
        font-weight: 400; color: #6B778C; font-size: 13px;
    }

    .jira-issues-header {
        padding: 20px 24px 12px; border-bottom: 1px solid #DFE1E6;
    }
    .jira-issues-title { font-size: 20px; font-weight: 500; color: #172B4D; margin: 0 0 12px; }
    .jira-filter-bar { display: flex; gap: 6px; flex-wrap: wrap; }
    .jira-filter-chip {
        display: inline-block; padding: 4px 10px; border-radius: 3px; font-size: 13px;
        text-decoration: none; color: #42526E; background: #F4F5F7; border: 1px solid transparent;
    }
    .jira-filter-chip:hover { background: #EBECF0; color: #172B4D; }
    .jira-filter-chip.active { background: #DEEBFF; color: #0052CC; font-weight: 500; border-color: #B3D4FF; }
    .jira-pagination {
        padding: 12px 24px; font-size: 13px; color: #6B778C;
        border-top: 1px solid #DFE1E6;
    }

    .jira-lozenge {
        display: inline-block; padding: 2px 4px; border-radius: 3px;
        font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px;
        white-space: nowrap;
    }
    .jira-lozenge-open, .jira-lozenge-todo { background: #DFE1E6; color: #42526E; }
    .jira-lozenge-progress { background: #DEEBFF; color: #0052CC; }
    .jira-lozenge-done { background: #E3FCEF; color: #006644; }

    .jira-label {
        display: inline-block; background: #DFE1E6; color: #42526E;
        padding: 2px 6px; border-radius: 3px; font-size: 11px; margin: 0 4px 4px 0;
    }
    .jira-label-trend { background: #FFEBE6; color: #BF2600; }

    .jira-detail-wrap { background: #fff; min-height: calc(100vh - 56px); }
    .jira-detail-main { padding: 16px 24px 24px; max-width: 900px; }
    .jira-detail-sidebar {
        background: #fff; border-left: 1px solid #DFE1E6;
        padding: 16px 20px; min-width: 280px;
    }
    .jira-detail-breadcrumb {
        font-size: 14px; color: #6B778C; margin-bottom: 8px;
    }
    .jira-detail-summary {
        font-size: 24px; font-weight: 500; color: #172B4D; margin: 0 0 12px; line-height: 1.3;
    }
    .jira-status-dropdown {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 10px; border: 1px solid #DFE1E6; border-radius: 3px;
        background: #FAFBFC; font-size: 14px; color: #172B4D; margin-bottom: 20px;
        cursor: default;
    }
    .jira-detail-section { margin-top: 24px; }
    .jira-detail-section h3 {
        font-size: 12px; font-weight: 600; color: #6B778C; text-transform: uppercase;
        letter-spacing: 0.5px; margin: 0 0 8px;
    }
    .jira-detail-desc {
        font-size: 14px; line-height: 1.6; color: #172B4D; white-space: pre-wrap;
        background: #fff; padding: 16px; border-radius: 3px; border: 1px solid #DFE1E6;
    }
    .jira-linked-evidence {
        background: #fff; border: 1px solid #DFE1E6; border-radius: 3px; padding: 16px;
        color: #6B778C; font-size: 14px;
    }
    .jira-evidence-list { display: grid; gap: 6px; margin-top: 12px; }
    .jira-evidence-ticket {
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
        padding: 9px 10px; border: 1px solid #DFE1E6; border-radius: 3px;
        color: #172B4D; text-decoration: none; background: #FAFBFC;
    }
    .jira-evidence-ticket:hover { background: #DEEBFF; color: #0052CC; }
    .jira-evidence-ticket-subject { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .jira-evidence-role {
        flex: 0 0 auto; padding: 2px 6px; border-radius: 3px;
        background: #DFE1E6; color: #42526E; font-size: 11px; font-weight: 600;
        text-transform: uppercase;
    }
    .jira-activity {
        background: #fff; border: 1px solid #DFE1E6; border-radius: 3px; padding: 16px;
    }
    .jira-activity-tabs {
        display: flex; gap: 16px; border-bottom: 1px solid #DFE1E6;
        margin: -16px -16px 16px; padding: 0 16px;
    }
    .jira-activity-tab {
        padding: 12px 0; font-size: 14px; color: #42526E; border-bottom: 2px solid transparent;
    }
    .jira-activity-tab.active {
        color: #0052CC; border-bottom-color: #0052CC; font-weight: 500;
    }
    .jira-activity-item {
        display: flex; gap: 12px; padding: 8px 0; font-size: 14px; color: #42526E;
        border-bottom: 1px solid #EBECF0;
    }
    .jira-activity-item:last-child { border-bottom: none; }
    .jira-activity-meta { font-size: 12px; color: #6B778C; margin-top: 2px; }

    .jira-details-panel h4 {
        font-size: 12px; font-weight: 600; color: #6B778C; text-transform: uppercase;
        letter-spacing: 0.5px; margin: 0 0 12px;
    }
    .jira-detail-field { margin-bottom: 16px; }
    .jira-detail-field dt {
        font-size: 12px; font-weight: 600; color: #6B778C; margin-bottom: 4px;
    }
    .jira-detail-field dd { margin: 0; font-size: 14px; color: #172B4D; }
    .jira-person { display: flex; align-items: center; gap: 8px; }

    .jira-impact-banner {
        background: #FFFAE6; border: 1px solid #FFE380; border-radius: 3px;
        padding: 12px 16px; margin-bottom: 20px; font-size: 14px; color: #172B4D;
    }
    .jira-impact-banner strong { color: #FF991F; }
    .jira-zd-link { color: #0052CC; text-decoration: none; font-size: 13px; display: inline-block; margin-top: 8px; }
    .jira-zd-link:hover { text-decoration: underline; }

    .jira-priority-urgent { color: #CD1316; font-weight: 600; }
    .jira-priority-high { color: #E94929; }
    .jira-priority-medium { color: #FF991F; }
    .jira-priority-low { color: #6B778C; }
    .jira-type { display: flex; align-items: center; gap: 4px; white-space: nowrap; font-size: 13px; }
</style>
"""

STATUS_FILTERS = [
    ("all", "All issues"),
    ("open", "Open"),
    ("in_progress", "In Progress"),
    ("done", "Done"),
    ("todo", "To Do"),
]

TYPE_ICONS = {
    "Bug": SVG_BUG,
    "Task": SVG_TASK,
    "Story": SVG_STORY,
}

SKIP_LABELS = {"support-escalation", "trend-warning"}

COMPONENT_PILLS = {
    "api": ("API", "jira-pill-api"),
    "billing": ("BILLING", "jira-pill-billing"),
    "mobile": ("MOBILE", "jira-pill-mobile"),
    "sso": ("ACCOUNTS", "jira-pill-accounts"),
    "export": ("EXPORT", "jira-pill-export"),
    "performance": ("PERFORMANCE", "jira-pill-performance"),
    "integrations": ("INTEGRATIONS", "jira-pill-integrations"),
    "database": ("DATABASE", "jira-pill-database"),
    "feature-flags": ("FLAGS", "jira-pill-feature-flags"),
    "notifications": ("NOTIFICATIONS", "jira-pill-notifications"),
    "feedback": ("FEEDBACK", "jira-pill-feedback"),
}

SPRINT_SIZE = 8
PAGE_SIZE = 25


def load_jira_issues() -> list[dict]:
    path = JIRA_ISSUES_PATH if JIRA_ISSUES_PATH.exists() else JIRA_SEED_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)["issues"]


def _write_jira_issues(issues: list[dict]) -> None:
    JIRA_ISSUES_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = JIRA_ISSUES_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"issues": issues}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(JIRA_ISSUES_PATH)


def _draft_issue_fields(ticket_id: str, draft: dict) -> dict:
    impact = draft.get("customer_impact") or {}
    category = draft.get("category", "support")
    return {
        "priority": str(draft.get("priority", "medium")).title(),
        "summary": draft.get("title", "Support trend investigation"),
        "description": draft.get("summary", "Support trend detected."),
        "labels": ["trend-warning", "support-escalation", category],
        "trigger_ticket_id": ticket_id,
        "similar_ticket_count": draft.get("similar_count", 0),
        "zendesk_ticket_count": impact.get("total_tickets", 0),
        "arr_at_risk": impact.get("arr_at_risk_formatted", "$0"),
    }


def create_jira_issue(ticket_id: str, draft: dict) -> dict:
    """Create or update one local Jira demo issue per trigger ticket."""
    issues = load_jira_issues()
    existing = issue_for_trigger_ticket(issues, ticket_id)
    if existing:
        existing.update(_draft_issue_fields(ticket_id, draft))
        _write_jira_issues(issues)
        return existing

    issue_numbers = [
        int(issue["key"].split("-", 1)[1])
        for issue in issues
        if issue.get("key", "").startswith(f"{PROJECT_KEY}-")
        and issue["key"].split("-", 1)[1].isdigit()
    ]
    issue = {
        "key": f"{PROJECT_KEY}-{max(issue_numbers, default=100) + 1}",
        "type": "Bug",
        "status": "Open",
        "assignee": "Unassigned",
        "reporter": "Support Operations",
        "created": date.today().isoformat(),
        **_draft_issue_fields(ticket_id, draft),
    }
    issues.append(issue)
    _write_jira_issues(issues)
    return issue


@st.cache_resource(show_spinner="Loading live trend data for Jira...")
def _get_similarity_cache() -> dict:
    return compute_embeddings()


def _live_trend_analysis(ticket_id: str) -> dict:
    reviewed = st.session_state.get(f"reviewed_trend_{ticket_id}") or load_confirmed_review(
        ticket_id
    )
    if reviewed:
        return reviewed

    cache = _get_similarity_cache()
    trend = detect_trend(cache, ticket_id)
    similar = find_similar(cache, ticket_id, top_k=5)
    impact = calculate_customer_impact(trend["similar_ids"], ticket_id)
    draft = generate_engineering_ticket(cache, ticket_id, trend, similar, impact)
    subjects_by_id = dict(zip(cache["ids"], cache["subjects"], strict=True))
    linked_support_tickets = [
        {
            "id": linked_id,
            "subject": subjects_by_id.get(linked_id, linked_id),
            "relationship": "Trigger" if linked_id == ticket_id else "Similar",
        }
        for linked_id in [ticket_id, *trend["similar_ids"]]
    ]
    return {
        "trend": trend,
        "impact": impact,
        "draft": draft,
        "linked_support_tickets": linked_support_tickets,
    }


def hydrate_linked_issue(issue: dict) -> dict:
    """Replace stored demo metrics with live analysis for trigger-linked issues."""
    ticket_id = issue.get("trigger_ticket_id")
    if not ticket_id:
        return issue

    try:
        analysis = _live_trend_analysis(ticket_id)
    except ValueError:
        # Historical Jira demo issues may reference tickets from an older dataset.
        return issue
    trend = analysis["trend"]
    impact = analysis["impact"]
    draft = analysis["draft"]

    hydrated = dict(issue)
    hydrated.update(
        {
            "summary": draft["title"],
            "description": draft["summary"],
            "priority": draft["priority"].title(),
            "similar_ticket_count": trend["similar_count"],
            "zendesk_ticket_count": impact["total_tickets"],
            "arr_at_risk": impact["arr_at_risk_formatted"],
            "analysis_source": "live",
            "linked_support_tickets": analysis.get("linked_support_tickets", []),
        }
    )
    return hydrated


def hydrate_linked_issues(issues: list[dict]) -> list[dict]:
    return [hydrate_linked_issue(issue) for issue in issues]


def _ticket_count(issue: dict) -> int:
    return issue.get("zendesk_ticket_count") or issue.get("linked_zendesk_tickets") or 0


def issue_by_key(issues: list[dict], key: str) -> dict | None:
    for issue in issues:
        if issue["key"] == key:
            return issue
    return None


def issue_for_trigger_ticket(issues: list[dict], ticket_id: str) -> dict | None:
    for issue in issues:
        if issue.get("trigger_ticket_id") == ticket_id:
            return issue
    return None


def _linked_support_evidence_html(issue: dict) -> str:
    tickets = issue.get("linked_support_tickets", [])
    if not tickets:
        return (
            '<div class="jira-linked-evidence">'
            "Supporting Zendesk ticket details are unavailable."
            "</div>"
        )

    rows = []
    for ticket in tickets:
        ticket_id = html.escape(ticket["id"])
        subject = html.escape(ticket["subject"])
        relationship = html.escape(ticket["relationship"])
        href = f"?ticket={html.escape(ticket['id'], quote=True)}&amp;mode=detail"
        rows.append(
            f'<a class="jira-evidence-ticket" href="{href}">'
            f'<span class="jira-evidence-ticket-subject"><strong>{ticket_id}</strong> &nbsp; {subject}</span>'
            f'<span class="jira-evidence-role">{relationship}</span>'
            "</a>"
        )

    return (
        '<div class="jira-linked-evidence">'
        '<strong style="color:#172B4D;">Zendesk evidence cluster</strong>'
        f'<div class="jira-evidence-list">{"".join(rows)}</div>'
        "</div>"
    )


def _jira_url(
    nav: str = "backlog",
    status_filter: str = "all",
    search: str = "",
    page: int = 0,
    issue: str | None = None,
) -> str:
    params = ["mode=jira"]
    if nav == "issues":
        params.append("nav=issues")
    if status_filter != "all":
        params.append(f"filter={html.escape(status_filter, quote=True)}")
    if search:
        params.append(f"jira_search={html.escape(search, quote=True)}")
    if page > 0:
        params.append(f"jira_page={page}")
    if issue:
        params.append(f"issue={html.escape(issue, quote=True)}")
    return "?" + "&".join(params)


def jira_issue_url(key: str, nav: str = "backlog", status_filter: str = "all") -> str:
    return _jira_url(nav=nav, status_filter=status_filter, issue=key)


def jira_view_in_jira_link(ticket_id: str) -> str | None:
    issues = load_jira_issues()
    issue = issue_for_trigger_ticket(issues, ticket_id)
    if not issue:
        return None
    return jira_issue_url(issue["key"])


def _status_lozenge_class(status: str) -> str:
    normalized = status.lower().replace(" ", "_")
    if normalized == "done":
        return "jira-lozenge-done"
    if normalized == "in_progress":
        return "jira-lozenge-progress"
    if normalized == "to_do":
        return "jira-lozenge-todo"
    return "jira-lozenge-open"


def _priority_class(priority: str) -> str:
    key = priority.lower()
    if key == "urgent":
        return "jira-priority-urgent"
    if key == "high":
        return "jira-priority-high"
    if key == "medium":
        return "jira-priority-medium"
    return "jira-priority-low"


def _filter_issues(issues: list[dict], status_filter: str, search: str = "") -> list[dict]:
    filtered = issues
    if status_filter != "all":
        mapping = {
            "open": "Open",
            "in_progress": "In Progress",
            "done": "Done",
            "todo": "To Do",
        }
        target = mapping.get(status_filter)
        if target:
            filtered = [i for i in filtered if i["status"] == target]
    if search:
        q = search.lower()
        filtered = [
            i
            for i in filtered
            if q in i["key"].lower()
            or q in i["summary"].lower()
            or q in i.get("assignee", "").lower()
            or q in i.get("reporter", "").lower()
            or any(q in label.lower() for label in i.get("labels", []))
        ]
    return filtered


def _type_icon(issue_type: str) -> str:
    return TYPE_ICONS.get(issue_type, SVG_TASK)


def _component_label(issue: dict) -> tuple[str, str] | None:
    for label in issue.get("labels", []):
        if label in SKIP_LABELS:
            continue
        if label in COMPONENT_PILLS:
            return COMPONENT_PILLS[label]
        text = label.replace("-", " ").upper()
        return text, "jira-pill-default"
    return None


def _avatar_html(name: str) -> str:
    if not name or name == "Unassigned":
        return '<span class="jira-avatar jira-avatar-unassigned" title="Unassigned">?</span>'
    parts = name.split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    hue = sum(ord(c) for c in name) % 360
    return (
        f'<span class="jira-avatar" style="background:hsl({hue},50%,48%)" '
        f'title="{html.escape(name)}">{html.escape(initials)}</span>'
    )


def _person_html(name: str) -> str:
    display = html.escape(name) if name else "Unassigned"
    return f'<div class="jira-person">{_avatar_html(name)}<span>{display}</span></div>'


def _issue_row_html(
    issue: dict,
    selected_key: str | None = None,
    nav: str = "backlog",
    status_filter: str = "all",
) -> str:
    key = html.escape(issue["key"])
    selected = " jira-row-selected" if issue["key"] == selected_key else ""
    href = jira_issue_url(issue["key"], nav=nav, status_filter=status_filter)
    pill_html = ""
    component = _component_label(issue)
    if component:
        text, cls = component
        pill_html = f'<span class="jira-pill {cls} jira-row-pill">{html.escape(text)}</span>'
    return (
        f'<div class="jira-issue-row{selected}">'
        f'<span class="jira-issue-type">{_type_icon(issue["type"])}</span>'
        f'<a class="jira-key" href="{href}">{key}</a>'
        f'<span class="jira-summary">{html.escape(issue["summary"])}</span>'
        f"{pill_html}"
        f'<span class="jira-row-avatar">{_avatar_html(issue.get("assignee", ""))}</span>'
        f"</div>"
    )


def render_jira_topbar():
    st.markdown(
        f"""
        <div class="jira-topbar">
            <div class="jira-topbar-logo">{SVG_JIRA_LOGO} Jira</div>
            <div class="jira-topbar-nav">
                <a href="?mode=jira">Your work</a>
                <a href="?mode=jira">Projects</a>
                <a href="?mode=jira&amp;nav=issues">Filters</a>
                <a href="?mode=jira">Dashboards</a>
                <a href="?mode=jira">Teams</a>
                <a href="?mode=jira">Plans</a>
                <a href="?mode=jira">Apps</a>
            </div>
            <div class="jira-topbar-search">{SVG_SEARCH} Search</div>
            <div class="jira-topbar-actions">
                <a class="jira-back-link" href="?mode=list">← Zendesk</a>
                <span class="jira-create-btn">Create</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_jira_sidebar(nav: str, status_filter: str):
    nav_links = []
    for key, icon, label, href in [
        ("roadmap", "🗺", "Roadmap", _jira_url(nav="backlog")),
        ("board", "▦", "Board", _jira_url(nav="backlog")),
        ("reports", "📊", "Reports", _jira_url(nav="backlog")),
        ("backlog", "☰", "Backlog", _jira_url(nav="backlog", status_filter=status_filter)),
        ("issues", "◫", "Issues", _jira_url(nav="issues", status_filter=status_filter)),
        ("deployments", "🚀", "Deployments", _jira_url(nav="backlog")),
        ("pages", "📄", "Pages", _jira_url(nav="backlog")),
    ]:
        active = " active" if nav == key else ""
        nav_links.append(
            f'<a class="jira-nav-item{active}" href="{href}">'
            f'<span class="jira-nav-icon">{icon}</span>{html.escape(label)}</a>'
        )

    filter_items = []
    if nav == "issues":
        for key, label in STATUS_FILTERS:
            active = " active" if status_filter == key else ""
            href = _jira_url(nav="issues", status_filter=key)
            filter_items.append(
                f'<a class="jira-filter-item{active}" href="{href}">{html.escape(label)}</a>'
            )

    filter_section = ""
    if filter_items:
        filter_section = (
            '<div class="jira-sidebar-divider"></div>'
            '<div class="jira-sidebar-section">Status</div>'
            + "".join(filter_items)
        )

    st.markdown(
        f"""
        <div class="jira-sidebar">
            <div class="jira-project-header">
                <a class="jira-project-header-link" href="{_jira_url(nav="backlog")}">
                    <span class="jira-project-icon">{PROJECT_KEY}</span>
                    <div>
                        <div class="jira-project-title">{html.escape(PROJECT_NAME)}</div>
                        <div class="jira-project-type">Software project</div>
                    </div>
                </a>
            </div>
            {"".join(nav_links)}
            <div class="jira-sidebar-divider"></div>
            <a class="jira-nav-item" href="{_jira_url(nav="backlog")}">
                <span class="jira-nav-icon">+</span>Add item
            </a>
            <a class="jira-nav-item" href="{_jira_url(nav="backlog")}">
                <span class="jira-nav-icon">⚙</span>Project settings
            </a>
            {filter_section}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_jira_backlog(
    issues: list[dict],
    total_count: int,
    status_filter: str = "all",
    selected_key: str | None = None,
):
    sprint_issues = issues[:SPRINT_SIZE]
    backlog_count = max(0, len(issues) - SPRINT_SIZE)
    sprint_rows = "".join(
        _issue_row_html(i, selected_key, nav="backlog", status_filter=status_filter)
        for i in sprint_issues
    )

    st.markdown(
        f"""
        <div class="jira-main">
            <div class="jira-board-header">
                <h1 class="jira-board-title">Backlog</h1>
                <div class="jira-board-actions">
                    <span class="jira-btn-secondary">Complete sprint</span>
                </div>
            </div>
            <div class="jira-sprint">
                <div class="jira-sprint-header">
                    <div>
                        <div class="jira-sprint-title">New sprint</div>
                        <div class="jira-sprint-meta">{len(sprint_issues)} issues</div>
                    </div>
                    <div class="jira-sprint-actions">
                        <span class="jira-btn-primary">Start sprint</span>
                    </div>
                </div>
                <div class="jira-issue-list">{sprint_rows}</div>
            </div>
            <div class="jira-backlog-section">
                <div class="jira-backlog-header">
                    {SVG_CHEVRON_RIGHT}
                    <span>Backlog</span>
                    <span class="jira-backlog-count">({backlog_count} issues)</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_jira_issues_list(
    issues: list[dict],
    total_count: int,
    page: int = 0,
    status_filter: str = "all",
    search: str = "",
    selected_key: str | None = None,
):
    start = page * PAGE_SIZE
    page_issues = issues[start : start + PAGE_SIZE]
    rows = "".join(
        _issue_row_html(i, selected_key, nav="issues", status_filter=status_filter)
        for i in page_issues
    )

    filter_chips = []
    for key, label in STATUS_FILTERS:
        active = " active" if status_filter == key else ""
        href = _jira_url(nav="issues", status_filter=key, search=search)
        filter_chips.append(
            f'<a class="jira-filter-chip{active}" href="{href}">{html.escape(label)}</a>'
        )

    end = min(start + PAGE_SIZE, len(issues))
    page_info = f"Showing {start + 1}–{end} of {len(issues)}" if issues else "0 issues"
    if len(issues) != total_count:
        page_info += f" (filtered from {total_count})"

    prev_href = next_href = ""
    if page > 0:
        prev_href = f'<a class="jira-key" href="{_jira_url(nav="issues", status_filter=status_filter, search=search, page=page - 1)}">← Previous</a>'
    if end < len(issues):
        next_href = f'<a class="jira-key" href="{_jira_url(nav="issues", status_filter=status_filter, search=search, page=page + 1)}">Next →</a>'

    st.markdown(
        f"""
        <div class="jira-main">
            <div class="jira-issues-header">
                <h1 class="jira-issues-title">Issues</h1>
                <div class="jira-filter-bar">{"".join(filter_chips)}</div>
            </div>
            <div class="jira-issue-list">
                {rows if rows else '<div style="padding:24px;color:#6B778C;">No issues match your filters.</div>'}
            </div>
            <div class="jira-pagination">{page_info} &nbsp; {prev_href} {next_href}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_jira_issue_detail(issue: dict, nav: str = "backlog", status_filter: str = "all"):
    labels_html = []
    for label in issue.get("labels", []):
        cls = "jira-label jira-label-trend" if label == "trend-warning" else "jira-label"
        labels_html.append(f'<span class="{cls}">{html.escape(label)}</span>')

    trigger = issue.get("trigger_ticket_id")
    zd_link = ""
    if trigger:
        zd_link = (
            f'<a class="jira-zd-link" href="?ticket={html.escape(trigger, quote=True)}&mode=detail">'
            f"View trigger ticket {html.escape(trigger)} in Zendesk →</a>"
        )

    lozenge = _status_lozenge_class(issue["status"])
    priority_cls = _priority_class(issue["priority"])
    reporter = issue.get("reporter", "Support Agent")
    ticket_count = _ticket_count(issue)
    similar_count = issue.get("similar_ticket_count")
    is_trend = issue.get("trigger_ticket_id") is not None
    arr = issue.get("arr_at_risk")
    ticket_count_text = f"{ticket_count} linked Zendesk tickets"
    if similar_count is not None:
        ticket_count_text = f"{similar_count} similar tickets + trigger ticket"

    impact_html = ""
    if arr or is_trend:
        trend_note = " · Escalated from Trend Detection Agent" if is_trend else ""
        impact_html = (
            f'<div class="jira-impact-banner">'
            f'<strong>ARR at risk:</strong> {html.escape(arr or "—")}'
            f' &nbsp;·&nbsp; {ticket_count_text}{trend_note}'
            f"</div>{zd_link}"
        )
    elif ticket_count:
        impact_html = (
            f'<div class="jira-impact-banner">'
            f'<strong>Support tickets:</strong> {ticket_count} linked Zendesk tickets'
            f"</div>"
        )

    evidence_html = (
        '<div class="jira-linked-evidence">No support evidence linked to this work item.</div>'
    )
    if is_trend:
        evidence_html = _linked_support_evidence_html(issue)

    activity_html = (
        '<div class="jira-activity">'
        '<div class="jira-activity-tabs">'
        '<span class="jira-activity-tab active">All</span>'
        '<span class="jira-activity-tab">Comments</span>'
        '<span class="jira-activity-tab">History</span>'
        '<span class="jira-activity-tab">Work log</span>'
        "</div>"
        '<div class="jira-activity-item">'
        f"{_avatar_html(reporter)}"
        "<div>"
        f"<div><strong>{html.escape(reporter)}</strong> created this issue</div>"
        f'<div class="jira-activity-meta">{html.escape(issue["created"])}</div>'
        "</div>"
        "</div>"
        '<div class="jira-activity-item">'
        f"{_avatar_html(issue.get('assignee', ''))}"
        "<div>"
        f"<div>Support escalation filed — {ticket_count} customer tickets referenced</div>"
        f'<div class="jira-activity-meta">{html.escape(issue["created"])}</div>'
        "</div>"
        "</div>"
        "</div>"
    )

    backlog_href = _jira_url(nav="backlog", status_filter=status_filter)
    issues_href = _jira_url(nav="issues", status_filter=status_filter)

    sidebar_html = (
        '<div class="jira-detail-sidebar jira-details-panel">'
        "<h4>Details</h4>"
        '<div class="jira-detail-field">'
        "<dt>Assignee</dt>"
        f"<dd>{_person_html(issue['assignee'])}</dd>"
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Reporter</dt>"
        f"<dd>{_person_html(reporter)}</dd>"
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Priority</dt>"
        f'<dd class="{priority_cls}">{html.escape(issue["priority"])}</dd>'
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Issue type</dt>"
        f'<dd><span class="jira-type">{_type_icon(issue["type"])} {html.escape(issue["type"])}</span></dd>'
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Labels</dt>"
        f'<dd>{"".join(labels_html) or "—"}</dd>'
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Created</dt>"
        f'<dd>{html.escape(issue["created"])}</dd>'
        "</div>"
        '<div class="jira-detail-field">'
        "<dt>Linked Zendesk tickets</dt>"
        f"<dd>{ticket_count}</dd>"
        "</div>"
        "</div>"
    )

    main_html = (
        '<div class="jira-detail-wrap"><div class="jira-detail-main">'
        '<div class="jira-detail-breadcrumb">'
        f'<a class="jira-key" href="{backlog_href}">Backlog</a> / '
        f'<a class="jira-key" href="{issues_href}">Issues</a> / '
        f'{html.escape(issue["key"])}'
        "</div>"
        f'<h1 class="jira-detail-summary">{html.escape(issue["summary"])}</h1>'
        '<div class="jira-status-dropdown">'
        f'<span class="jira-lozenge {lozenge}">{html.escape(issue["status"])}</span>'
        f"{SVG_CHEVRON}"
        "</div>"
        f"{impact_html}"
        '<div class="jira-detail-section">'
        "<h3>Description</h3>"
        f'<div class="jira-detail-desc">{html.escape(issue.get("description", ""))}</div>'
        "</div>"
        '<div class="jira-detail-section">'
        "<h3>Linked support evidence</h3>"
        f"{evidence_html}"
        "</div>"
        '<div class="jira-detail-section">'
        "<h3>Activity</h3>"
        f"{activity_html}"
        "</div>"
        "</div></div>"
    )

    st.markdown(
        f'<div style="display:flex;align-items:flex-start;">{main_html}{sidebar_html}</div>',
        unsafe_allow_html=True,
    )


def render_jira_view(
    issue_key: str | None = None,
    status_filter: str = "all",
    search: str = "",
    page: int = 0,
    nav: str = "backlog",
):
    issues = hydrate_linked_issues(load_jira_issues())
    total_count = len(issues)
    filtered = _filter_issues(issues, status_filter, search)
    is_detail = issue_key is not None
    issue = issue_by_key(issues, issue_key) if is_detail else None

    render_jira_topbar()

    col_sidebar, col_main = st.columns([0.18, 0.82])
    with col_sidebar:
        render_jira_sidebar(nav, status_filter)
    with col_main:
        if is_detail and issue:
            render_jira_issue_detail(issue, nav=nav, status_filter=status_filter)
        elif is_detail:
            st.markdown(
                '<div class="jira-main" style="padding:24px;">'
                "<p>Issue not found.</p>"
                f'<a class="jira-key" href="{_jira_url(nav=nav)}">← Back to list</a>'
                "</div>",
                unsafe_allow_html=True,
            )
        elif nav == "issues":
            render_jira_issues_list(
                filtered,
                total_count=total_count,
                page=page,
                status_filter=status_filter,
                search=search,
            )
        else:
            render_jira_backlog(
                filtered,
                total_count=total_count,
                status_filter=status_filter,
            )
