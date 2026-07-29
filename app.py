"""Trend Detection Agent — Zendesk-style helpdesk demo."""

import html
import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from escalation_quality_bridge import format_quality_summary, score_draft
from similarity import (
    DB_PATH,
    compute_embeddings,
    detect_trend,
    detect_trends_batch,
    find_similar,
    format_engineering_ticket_text,
    generate_engineering_ticket,
)
from impact import calculate_customer_impact, format_arr, load_accounts
from jira_view import (
    JIRA_CSS,
    jira_view_in_jira_link,
    render_jira_view,
)
from trend_view import render_trend_dashboard, trend_dashboard_url
from trend_review_store import load_confirmed_review

ROOT = Path(__file__).resolve().parent
DEMO_PATH = ROOT / "demo_scenarios.json"
CONVERSATIONS_PATH = ROOT / "data" / "runtime" / "conversations.json"
API_BASE = "http://127.0.0.1:8000"
PAGE_SIZE = 40

REQUESTER_NAMES = [
    "Sarah Chen", "Peter Tailby", "Marcus Webb", "Elena Torres",
    "James Okonkwo", "Priya Sharma", "David Lindstrom", "Anna Kowalski",
    "Michael Reyes", "Sophie Laurent", "Chris Nakamura", "Rachel Bloom",
    "Tom Bradley", "Nina Patel", "Alex Ferguson", "Julia Mendez",
]
AGENT_NAMES = [
    "Lisa Kelly", "Support/John", "Maria Santos", "David Chen",
    "Support/Emma", "James Wright", "—", "Support/Priya",
]
CHANNELS = ["Email", "Chat", "API"]

FORM_LABELS = {
    "api": "API Support",
    "billing": "Billing",
    "technical": "Technical",
    "cancellation": "Cancellation",
    "complaint": "Complaints",
    "upgrade": "Upgrades",
}

PRIORITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "urgent": "Urgent",
}

VIEW_LABELS = {
    "api": "API Issues",
    "billing": "Billing",
    "technical": "Technical Support",
    "cancellation": "Cancellations",
    "complaint": "Complaints",
    "upgrade": "Upgrades",
    "unsolved": "Your unsolved tickets",
    "unassigned": "Unassigned tickets",
    "open": "All open tickets",
}

VIEW_ORDER = ["api", "billing", "technical", "cancellation", "complaint", "upgrade"]

SVG_HOME = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 10.5L12 4l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V10.5z"/><path d="M9 21V12h6v9"/></svg>'
SVG_TICKET = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 6a2 2 0 012-2h1l1-2h8l1 2h1a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6z"/><path d="M9 10h6M9 14h4"/></svg>'
SVG_USERS = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M14 20c.3-2.2 2-4 4.5-4 1.2 0 2.3.4 3.1 1.1"/></svg>'
SVG_CHART = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 20V10M10 20V4M16 20v-7M22 20v-12"/></svg>'
SVG_GEAR = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>'
SVG_SEARCH = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#68737D" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/></svg>'
SVG_GRID = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
SVG_PHONE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>'
SVG_CHAT_OUTLINE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
SVG_MSG_FILLED = '<svg width="14" height="14" viewBox="0 0 24 24" fill="#fff"><path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/></svg>'
SVG_USER_FILLED = '<svg width="14" height="14" viewBox="0 0 24 24" fill="#fff"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>'
SVG_TALK_FILLED = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/></svg>'
SVG_VIEW_BOX = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#68737d" stroke-width="1.75"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>'
SVG_PLAY = '<svg width="14" height="14" viewBox="0 0 24 24" fill="#68737d"><path d="M8 5v14l11-7z"/></svg>'
SVG_CLOSE = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>'
SVG_JIRA = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none">'
    '<path d="M11.5 2L2 12.5l9.5 9.5 9.5-9.5L11.5 2z" fill="#2684FF"/>'
    '<path d="M11.5 6.5L6 12l5.5 5.5L17 12l-5.5-5.5z" fill="#0052CC"/>'
    "</svg>"
)

ZENDESK_CSS = """
<style>
    #MainMenu, footer, header, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    .stDeployButton, [data-testid="stHeader"], header[data-testid="stHeader"] {
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }
    .block-container, .stMainBlockContainer,
    [data-testid="stMainBlockContainer"] {
        padding: 0 !important; padding-top: 0 !important;
        max-width: 100% !important; margin-top: 0 !important;
    }
    [data-testid="stAppViewContainer"], .stApp { background: #f8f9f9; margin-top: 0 !important; }
    [data-testid="stAppViewContainer"] > section.main > div,
    section.main > div, [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important; padding-bottom: 0 !important; gap: 0 !important;
    }
    [data-testid="stVerticalBlock"] { gap: 0 !important; }
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; }
    [data-testid="stVerticalBlock"] > div { gap: 0 !important; }
    [data-testid="column"], [data-testid="stColumn"] { padding: 0 !important; }
    [data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: flex-start !important; }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) {
        flex-wrap: nowrap !important;
        width: 100% !important;
    }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(1),
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(1) {
        flex: 0 0 52px !important; width: 52px !important; min-width: 52px !important;
        max-width: 52px !important;
    }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(2),
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(2) {
        flex: 0 0 220px !important; width: 220px !important; min-width: 220px !important;
        max-width: 220px !important;
        background: #f8f9f9; border-right: 1px solid #d8dcde;
        min-height: calc(100vh - 52px);
    }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(3),
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(3) {
        flex: 1 1 0% !important; flex-basis: 0 !important; background: #fff;
        width: auto !important; min-width: 0 !important; max-width: none !important;
        min-height: calc(100vh - 52px);
        overflow-x: auto !important;
    }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(4),
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(4) {
        flex: 0 0 420px !important; width: 420px !important; min-width: 420px !important;
        max-width: 40% !important;
        background: #f8f9f9; border-left: 1px solid #d8dcde;
        min-height: calc(100vh - 52px);
    }

    body.zd-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(1):not(:has(.zd-props)):not(:has(.zd-conv-panel)):not(:has(.zd-context)),
    body.zd-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(1):not(:has(.zd-props)):not(:has(.zd-conv-panel)):not(:has(.zd-context)) {
        flex: 0 0 52px !important; width: 52px !important; min-width: 52px !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(2),
    body.zd-detail-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 auto !important; min-width: 0 !important;
        background: #f8f9f9; min-height: calc(100vh - 52px);
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]:has(.zd-props) {
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        overflow: hidden !important;
        align-items: stretch !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1),
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex: 0 0 220px !important; width: 220px !important; min-width: 220px !important;
        max-width: 220px !important;
        background: #fff; border-right: 1px solid #d8dcde;
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        overflow-y: auto !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) [data-testid="stVerticalBlock"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 auto !important; min-width: 0 !important; background: #fff;
        border-right: 1px solid #d8dcde;
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        overflow: hidden !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlock"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlock"] {
        height: 100% !important;
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }
    body.zd-detail-mode [data-testid="element-container"]:has(.zd-conv-panel),
    body.zd-detail-mode [data-testid="stElementContainer"]:has(.zd-conv-panel) {
        height: 100% !important;
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        min-height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3),
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
        flex: 0 0 400px !important; width: 400px !important; min-width: 400px !important;
        max-width: 400px !important;
        background: #f8f9f9; border-left: 1px solid #d8dcde;
        max-height: calc(100vh - var(--zd-detail-chrome, 268px)) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) [data-testid="stVerticalBlock"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) [data-testid="element-container"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) [data-testid="stElementContainer"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="element-container"],
    body.zd-detail-mode [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stElementContainer"] {
        background: transparent !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        font-size: 13px;
        color: #2f3941;
    }
    h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2 {
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #2f3941 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Global top bar — Zendesk utility icons */
    .zd-global-bar {
        background: #fff; border-bottom: 1px solid #d8dcde;
        min-height: 52px; height: auto;
        padding: 10px 12px 10px 8px;
        display: flex; align-items: center; gap: 8px;
        flex-shrink: 0; overflow: visible;
        line-height: 1; box-sizing: border-box;
        position: relative; z-index: 3;
    }
    .zd-global-spacer { flex: 1; }
    .zd-global-search {
        display: flex; align-items: center; gap: 6px;
        padding: 0 10px; border: 1px solid #d8dcde; border-radius: 4px;
        background: #f8f9f9; color: #87929d; font-size: 13px; min-width: 200px;
        line-height: 1.4; flex-shrink: 0;
    }
    .zd-global-search svg { display: block; flex-shrink: 0; margin-left: 2px; }
    .zd-global-search-input {
        flex: 1; min-width: 0; border: none; background: transparent;
        color: #2f3941; font-size: 13px; line-height: 1.4;
        padding: 6px 0; outline: none; font-family: inherit;
        pointer-events: auto; user-select: text;
    }
    [data-testid="stCustomComponentV1"] iframe[height="0"],
    [data-testid="stCustomComponentV1"] iframe[style*="height: 0"] {
        pointer-events: none !important;
    }
    .zd-global-search-input::placeholder { color: #87929d; }
    .zd-global-search-input::-webkit-search-cancel-button { cursor: pointer; }
    .zd-global-icons {
        display: flex; align-items: center; gap: 4px;
        flex-shrink: 0; overflow: visible;
    }
    .zd-icon-btn {
        width: 32px; height: 32px; min-width: 32px; min-height: 32px;
        border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        color: #68737d; cursor: default; position: relative;
        flex-shrink: 0; line-height: 0; overflow: visible;
    }
    .zd-icon-btn svg { display: block; flex-shrink: 0; }
    .zd-icon-btn:hover { background: #f3f4f4; }
    .zd-icon-filled {
        width: 32px; height: 32px; min-width: 32px; min-height: 32px;
        border-radius: 4px;
        background: #2f3941;
        display: flex; align-items: center; justify-content: center;
        cursor: default; position: relative;
        flex-shrink: 0; line-height: 0; overflow: visible;
    }
    .zd-icon-filled svg { display: block; flex-shrink: 0; }
    .zd-icon-filled:hover { background: #03363d; }
    .zd-notify-dot {
        position: absolute; top: 3px; right: 3px;
        width: 8px; height: 8px; border-radius: 50%;
        background: #cc3340; border: 1.5px solid #fff;
    }
    .zd-profile-initials {
        width: 28px; height: 28px; min-width: 28px; min-height: 28px;
        border-radius: 50%;
        background: #5c6970; color: #fff;
        font-size: 11px; font-weight: 600; line-height: 1;
        display: flex; align-items: center; justify-content: center;
        border: 2px solid #fff; box-shadow: 0 0 0 1px #d8dcde;
        margin-left: 4px; cursor: default; position: relative;
        flex-shrink: 0; overflow: visible;
    }
    .zd-profile-initials::after {
        content: ""; position: absolute; bottom: -1px; right: -1px;
        width: 8px; height: 8px; border-radius: 50%;
        background: #038153; border: 2px solid #fff;
    }

    /* Prevent Streamlit parent blocks from clipping header/tab chrome */
    [data-testid="stMarkdownContainer"]:has(.zd-global-bar),
    [data-testid="stMarkdownContainer"]:has(.zd-tab-bar) {
        overflow: visible !important;
    }
    [data-testid="element-container"]:has(.zd-global-bar),
    [data-testid="stElementContainer"]:has(.zd-global-bar) {
        overflow: visible !important;
        min-height: 52px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="element-container"]:has(.zd-tab-bar),
    [data-testid="stElementContainer"]:has(.zd-tab-bar) {
        overflow: visible !important;
        min-height: 41px !important;
        margin: 0 0 12px 0 !important;
        padding: 0 !important;
    }
    [data-testid="element-container"]:has(.zd-view-header),
    [data-testid="stElementContainer"]:has(.zd-view-header) {
        overflow: visible !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stVerticalBlock"] > [data-testid="element-container"]:first-child:has(.zd-global-bar),
    [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child:has(.zd-global-bar) {
        margin-bottom: 0 !important;
    }

    /* View tab strip — Zendesk Agent Workspace */
    .zd-tab-bar {
        background: #f4f5f5; border-bottom: 1px solid #d8dcde;
        min-height: 41px; height: auto;
        padding: 4px 8px 8px;
        display: flex; align-items: flex-end; gap: 2px;
        flex-shrink: 0; overflow: visible;
        position: relative; z-index: 1;
        margin-top: 0;
        margin-bottom: 0;
    }
    .zd-tab-add {
        display: inline-flex; align-items: center;
        padding: 7px 10px; margin-bottom: 0;
        border: none; background: transparent;
        color: #2f3941; font-size: 13px; font-weight: 500;
        cursor: default; border-radius: 4px 4px 0 0;
        white-space: nowrap;
    }
    .zd-tab-add:hover { background: #e9ebed; }
    .zd-tab-chip {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 7px 8px 7px 12px;
        background: #fff;
        border: 1px solid #d8dcde;
        border-bottom: 1px solid #fff;
        border-radius: 4px 4px 0 0;
        font-size: 13px; font-weight: 500; color: #2f3941;
        margin-bottom: -1px; cursor: default;
        white-space: nowrap; max-width: 320px;
        overflow: hidden; text-overflow: ellipsis;
    }
    .zd-tab-close {
        display: flex; align-items: center; justify-content: center;
        width: 18px; height: 18px; border-radius: 3px;
        color: #68737d; cursor: default; flex-shrink: 0;
    }
    .zd-tab-close:hover { background: #f3f4f4; color: #2f3941; }

    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) {
        background: #fff; border-bottom: 1px solid #d8dcde;
        min-height: 52px; max-height: 52px; height: 52px;
        align-items: center !important;
        padding: 10px 12px 10px 8px; position: relative; z-index: 3;
        flex-shrink: 0; box-sizing: border-box;
        overflow: visible !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="column"]:nth-child(1),
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="stColumn"]:nth-child(1) {
        flex: 1 1 auto !important; width: auto !important; min-width: 0 !important;
        min-height: 0 !important; background: transparent !important;
        border: none !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="column"]:nth-child(2),
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="stColumn"]:nth-child(2) {
        flex: 0 0 auto !important; width: auto !important; min-width: 200px !important;
        max-width: 280px !important; min-height: 0 !important;
        background: transparent !important; border: none !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="column"]:nth-child(3),
    [data-testid="stHorizontalBlock"]:has(.st-key-header_search) > [data-testid="stColumn"]:nth-child(3) {
        flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
        min-height: 0 !important; background: transparent !important;
        border: none !important;
        display: flex !important; justify-content: flex-end !important;
    }
    [data-testid="stForm"]:has(.st-key-header_search) {
        border: none !important; padding: 0 !important; margin: 0 !important;
    }
    [data-testid="stForm"]:has(.st-key-header_search) [data-testid="stFormSubmitButton"] {
        position: absolute !important; width: 1px !important; height: 1px !important;
        overflow: hidden !important; clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important; border: 0 !important; padding: 0 !important; margin: 0 !important;
    }
    .st-key-header_search { position: relative; min-width: 200px; max-width: 280px; margin-left: auto; }
    .st-key-header_search [data-testid="stTextInput"] { margin: 0 !important; }
    .st-key-header_search input,
    .st-key-header_search [data-testid="stTextInput"] input {
        background: #f8f9f9 !important;
        border: 1px solid #d8dcde !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        color: #2f3941 !important;
        padding: 6px 12px 6px 32px !important;
        box-shadow: none !important;
        height: 32px !important;
        min-height: 32px !important;
    }
    .st-key-header_search input:focus,
    .st-key-header_search [data-testid="stTextInput"] input:focus {
        border-color: #1f73b7 !important;
        box-shadow: 0 0 0 1px #1f73b7 !important;
    }
    .st-key-header_search input::placeholder { color: #87929d !important; }
    .st-key-header_search::before {
        content: "";
        position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
        width: 15px; height: 15px; z-index: 2; pointer-events: none;
        background: no-repeat center / contain url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='%2368737D' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='M20 20l-3-3'/%3E%3C/svg%3E");
    }

    .zd-icon-nav {
        width: 52px; min-width: 52px; height: calc(100vh - 52px);
        background: #03363d;
        display: flex; flex-direction: column; align-items: center;
        padding: 8px 0; gap: 2px;
    }
    .zd-icon-nav .zd-icon {
        width: 40px; height: 40px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 4px; color: #8bb5b8; cursor: default;
        border-left: 3px solid transparent;
    }
    .zd-icon-nav .zd-icon.active {
        background: #17494d; color: #fff;
        border-left-color: #30aabc;
    }
    .zd-icon-nav .zd-icon:hover { color: #fff; }
    .zd-icon-nav a.zd-icon { text-decoration: none; }

    .jira-zd-link { color: #0052CC; text-decoration: none; font-size: 13px; }
    .jira-zd-link:hover { text-decoration: underline; }
    .jira-zd-create {
        display: inline-block; margin-top: 10px; padding: 7px 10px; border-radius: 3px;
        background: #03363d; border: 1px solid #03363d; color: #fff !important;
        text-decoration: none !important; font-size: 12px; font-weight: 600;
    }
    .jira-zd-create:hover { background: #17494d; border-color: #17494d; }

    .zd-views { background: #f8f9f9; }
    .zd-views-top {
        padding: 10px 16px 6px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .zd-views-header {
        font-size: 13px; font-weight: 600; color: #2f3941;
    }
    .zd-views-actions {
        color: #68737d; font-size: 13px; display: flex; gap: 10px;
        cursor: default; user-select: none;
    }
    .zd-view-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 16px 5px 13px;
        font-size: 13px; color: #2f3941; text-decoration: none !important;
        border-left: 3px solid transparent; line-height: 1.35;
        cursor: pointer;
    }
    .zd-view-item:visited, .zd-view-item:link { color: #2f3941; text-decoration: none !important; }
    .zd-view-item:hover { background: #f3f4f4; color: #2f3941; text-decoration: none !important; }
    .zd-view-item.active {
        background: #e9ebed; border-left-color: #03363d;
    }
    .zd-view-item.active .zd-view-name { font-weight: 600; }
    .zd-view-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .zd-view-count {
        color: #68737d; font-size: 13px; font-weight: 400;
        margin-left: 8px; flex-shrink: 0;
    }
    .zd-views-divider {
        height: 1px; background: #e9ebed; margin: 8px 0;
    }
    .zd-demo-section {
        margin-top: 16px; padding-top: 10px;
        border-top: 1px solid #e9ebed;
    }
    .zd-demo-label {
        padding: 0 14px 4px;
        font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em; color: #68737d;
    }

    .zd-list-shell {
        background: #fff; display: flex; flex-direction: column;
    }
    .zd-detail-shell {
        background: #fff; display: flex; flex-direction: column;
        padding-top: 16px;
    }
    body.zd-detail-mode [data-testid="element-container"]:has(.zd-detail-shell),
    body.zd-detail-mode [data-testid="stElementContainer"]:has(.zd-detail-shell),
    [data-testid="element-container"]:has(.zd-detail-shell),
    [data-testid="stElementContainer"]:has(.zd-detail-shell) {
        padding-top: 16px !important;
        margin: 0 !important;
    }
    .zd-detail-tab-gap {
        display: block !important;
        height: 16px !important;
        min-height: 16px !important;
        background: #fff;
        margin: 0;
        padding: 0;
        flex-shrink: 0;
        line-height: 16px;
        font-size: 0;
    }
    body.zd-detail-mode [data-testid="element-container"]:has(.zd-detail-tab-gap),
    body.zd-detail-mode [data-testid="stElementContainer"]:has(.zd-detail-tab-gap),
    [data-testid="element-container"]:has(.zd-detail-tab-gap),
    [data-testid="stElementContainer"]:has(.zd-detail-tab-gap) {
        margin: 0 !important;
        padding: 0 !important;
        min-height: 16px !important;
        height: 16px !important;
    }
    body.zd-detail-mode .st-key-back_to_list,
    .st-key-back_to_list {
        background: #fff !important;
        border-bottom: 1px solid #e9ebed !important;
        margin: 0 !important;
        padding: 12px 0 0 !important;
        position: relative;
        z-index: 1;
        flex-shrink: 0;
    }
    body.zd-detail-mode .st-key-back_to_list [data-testid="stVerticalBlock"],
    .st-key-back_to_list [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        padding-top: 0 !important;
    }
    .zd-view-header {
        background: #fff; border-bottom: 1px solid #d8dcde;
        margin-top: 10px;
        padding: 22px 16px 10px;
        flex-shrink: 0;
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px;
    }
    .zd-view-header-left { min-width: 0; }
    .zd-view-title-row {
        display: flex; align-items: center; gap: 8px;
    }
    .zd-view-title-row svg { flex-shrink: 0; }
    .zd-play-btn {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 12px; border: 1px solid #d8dcde; border-radius: 4px;
        background: #fff; color: #68737d; font-size: 13px;
        cursor: default; flex-shrink: 0; opacity: 0.75;
    }
    .zd-play-btn:hover { background: #f8f9f9; opacity: 1; }
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(3) [data-testid="element-container"],
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="column"]:nth-child(3) [data-testid="stElementContainer"],
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(3) [data-testid="element-container"],
    body.zd-list-mode [data-testid="stHorizontalBlock"]:not(:has(.st-key-header_search)) > [data-testid="stColumn"]:nth-child(3) [data-testid="stElementContainer"] {
        padding-left: 0 !important; padding-right: 0 !important;
    }
    .zd-view-title { font-size: 18px; font-weight: 600; color: #2f3941; line-height: 1.2; }
    .zd-view-subtitle { font-size: 12px; color: #68737d; margin-top: 2px; }

    .zd-table-area { background: #fff; }
    .zd-table-wrap { background: #fff; padding: 0 16px; overflow-x: auto; }
    .zd-table { width: 100%; min-width: 800px; border-collapse: collapse; table-layout: fixed; }
    .zd-table thead th {
        background: #f4f5f5; border-bottom: 1px solid #d8dcde;
        padding: 6px 8px; text-align: left; font-weight: 600;
        color: #68737d; font-size: 11px; white-space: nowrap;
    }
    .zd-table tbody tr {
        border-bottom: 1px solid #e9ebed; cursor: pointer;
        transition: background 0.06s;
    }
    .zd-table tbody tr:hover { background: #f8f9f9; }
    .zd-table tbody tr.zd-row-trend { background: #fffdf4; }
    .zd-table tbody tr.zd-row-trend:hover { background: #fff9df; }
    .zd-table tbody tr.selected {
        background: #e9f2f9; box-shadow: inset 3px 0 0 #03363d;
    }
    .zd-table td {
        padding: 5px 8px; color: #2f3941;
        vertical-align: middle; overflow: hidden;
        text-overflow: ellipsis; white-space: nowrap;
        font-size: 13px; height: 30px;
    }
    .zd-table a { color: #1f73b7; text-decoration: none; }
    .zd-table a:hover { text-decoration: underline; }
    .zd-table .subj-link { color: #2f3941; }
    .zd-table .col-check { width: 28px; text-align: center; color: #c2c8cc; }
    .zd-table .col-status { width: 28px; }
    .zd-table .col-status-label { width: 76px; }
    .status-badge {
        display: inline-block; padding: 1px 7px; border-radius: 3px;
        font-size: 11px; font-weight: 500; line-height: 1.4;
    }
    .zd-table .col-id { width: 58px; }
    .zd-table .col-subject { width: 210px; max-width: 210px; }
    .zd-table .col-channel { width: 82px; color: #68737d; font-size: 12px; }
    .zd-table .col-requester { width: 120px; }
    .zd-table .col-date { width: 74px; color: #68737d; font-size: 12px; }
    .zd-table .col-assignee { width: 102px; color: #68737d; font-size: 12px; }
    .zd-trend-warning {
        display: inline-flex; align-items: center; gap: 4px;
        margin-left: 7px; padding: 2px 6px;
        border: 1px solid #d6a300; border-radius: 3px;
        background: #fff3c2; color: #624500;
        font-size: 10px; font-weight: 700; line-height: 1.35;
        white-space: nowrap; vertical-align: middle;
    }
    .status-sq {
        display: inline-flex; align-items: center; justify-content: center;
        width: 20px; height: 20px; border-radius: 2px;
        font-size: 10px; font-weight: 700; color: #fff;
    }
    .status-open { background: #cc3340; }
    .status-pending { background: #1f73b7; }
    .status-resolved { background: #038153; }
    .status-closed { background: #87929d; }
    .status-new { background: #ffc800; color: #2f3941; }
    .zd-pagination {
        padding: 8px 16px; border-top: 1px solid #e9ebed;
        display: flex; align-items: center; justify-content: space-between;
        font-size: 12px; color: #68737d; background: #fff;
    }
    .zd-page-nums { display: flex; gap: 2px; align-items: center; }
    .zd-page-num {
        display: inline-flex; align-items: center; justify-content: center;
        min-width: 24px; height: 24px; padding: 0 5px;
        border: 1px solid transparent; border-radius: 3px;
        color: #68737d; text-decoration: none; font-size: 12px;
    }
    .zd-page-num:hover { background: #f3f4f4; border-color: #d8dcde; }
    .zd-page-num.active {
        background: #e9ebed; border-color: #c2c8cc;
        color: #2f3941; font-weight: 600;
    }
    .zd-page-num.disabled { color: #c2c8cc; pointer-events: none; }

    .badge-open { background: #cc3340; color: #fff; }
    .badge-pending { background: #1f73b7; color: #fff; }
    .badge-resolved { background: #038153; color: #fff; }
    .badge-closed { background: #87929d; color: #fff; }
    .badge-new { background: #ffc800; color: #2f3941; }
    .status-badge.badge-open { background: #fde8e8; color: #cc3340; }
    .status-badge.badge-pending { background: #e3f0fa; color: #1f73b7; }
    .status-badge.badge-resolved { background: #e6f4ed; color: #038153; }
    .status-badge.badge-closed { background: #e9ebed; color: #68737d; }
    .status-badge.badge-new { background: #fff8e0; color: #9a7b00; }
    .zd-tag-chip {
        display: inline-block; background: #e9ebed; color: #49545c;
        padding: 2px 6px; border-radius: 3px; font-size: 11px; margin: 0 4px 4px 0;
    }

    /* Hover popup — Zendesk-style floating card on row hover */
    .zd-table tbody tr { position: relative; }
    .zd-hover-popup {
        display: none; position: fixed;
        width: 400px; max-width: calc(100vw - 32px);
        background: #fff; border-radius: 4px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.06);
        padding: 16px 20px 14px; z-index: 99999;
        pointer-events: none; text-align: left;
        white-space: normal; line-height: 1.45;
    }
    .zd-hover-popup.visible { display: block; }
    .zd-hover-top {
        display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
    }
    .zd-hover-badge {
        display: inline-block; padding: 3px 9px; border-radius: 3px;
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.04em; flex-shrink: 0;
    }
    .zd-hover-id { font-size: 12px; color: #68737d; }
    .zd-hover-subject {
        font-size: 15px; font-weight: 600; color: #2f3941;
        margin-bottom: 6px; line-height: 1.35;
        overflow: hidden; text-overflow: ellipsis;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    }
    .zd-hover-body {
        font-size: 13px; color: #49545c; margin-bottom: 12px; line-height: 1.5;
        overflow: hidden; text-overflow: ellipsis;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    }
    .zd-hover-latest-label {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #87929d; margin-bottom: 6px;
        border-top: 1px solid #e9ebed; padding-top: 10px;
    }
    .zd-hover-latest-header {
        display: flex; justify-content: space-between; align-items: baseline;
        font-size: 12px; margin-bottom: 4px;
    }
    .zd-hover-latest-header strong { color: #2f3941; font-weight: 600; }
    .zd-hover-latest-header span { color: #68737d; }
    .zd-hover-latest-text {
        font-size: 13px; color: #49545c; line-height: 1.45;
        overflow: hidden; text-overflow: ellipsis;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    }
    .zd-hover-meta {
        font-size: 11px; color: #87929d; margin-top: 10px;
        border-top: 1px solid #e9ebed; padding-top: 8px;
    }

    .zd-agent { padding: 0 12px 16px; box-sizing: border-box; }
    .zd-agent-card {
        background: #fff; border: 1px solid #d8dcde; border-radius: 4px;
        padding: 0; box-sizing: border-box;
        overflow: hidden;
    }
    .zd-agent-card-pad {
        padding: 14px 16px 0; box-sizing: border-box;
    }
    .zd-agent-card-pad-bottom {
        padding: 10px 16px 14px;
    }
    .zd-agent-card-list {
        padding: 14px 16px;
    }
    .zd-analyze-btn {
        display: block; width: 100%; box-sizing: border-box;
        margin: 0; padding: 7px 16px;
        background: #03363d; border: none; border-top: 1px solid #d8dcde;
        border-bottom: 1px solid #d8dcde;
        border-radius: 0; color: #fff !important; font-size: 13px; font-weight: 500;
        cursor: pointer; font-family: inherit; line-height: 1.4;
        text-align: center; text-decoration: none !important; outline: none;
    }
    .zd-analyze-btn:hover, .zd-analyze-btn:focus {
        background: #17494d; color: #fff !important; text-decoration: none !important;
    }
    .zd-apps-divider {
        height: 1px; background: #d8dcde; margin: 0;
    }
    .zd-apps-header {
        padding: 10px 12px 6px; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em; color: #68737d;
    }
    .zd-agent-product {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: #87929d; margin-bottom: 4px;
    }
    .zd-agent-title { font-size: 16px; font-weight: 600; color: #2f3941; margin-bottom: 4px; }
    .zd-agent-sub { font-size: 13px; color: #68737d; margin-bottom: 14px; }
    .trend-alert {
        background: #fff8e6; border: 1px solid #e9ebed;
        border-left: 3px solid #f5a623; border-radius: 3px;
        padding: 9px 11px; font-size: 13px; color: #5c4a00; margin-bottom: 10px;
    }
    .trend-alert strong { color: #2f3941; font-weight: 600; }
    .trend-ok {
        background: #f0f9f4; border: 1px solid #e9ebed;
        border-left: 3px solid #038153; border-radius: 3px;
        padding: 9px 11px; font-size: 13px; color: #0b5124; margin-bottom: 10px;
    }
    .trend-ok strong { color: #2f3941; font-weight: 600; }
    .zd-section-label {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #68737d; margin: 12px 0 6px;
    }
    .similar-row {
        display: block; color: #2f3941; text-decoration: none;
        background: #f8f9f9; border: 1px solid #e9ebed; border-radius: 3px;
        padding: 8px 12px; margin-bottom: 6px; font-size: 13px; line-height: 1.45;
    }
    .similar-row:hover { background: #edf7ff; border-color: #1f73b7; color: #144a75; }
    .draft-box {
        background: #f8f9f9; border: 1px solid #d8dcde; border-radius: 3px;
        padding: 12px; font-size: 12px;
        font-family: "SF Mono", Consolas, "Liberation Mono", monospace;
        white-space: pre-wrap; max-height: 240px; overflow-y: auto;
        line-height: 1.5; margin-bottom: 10px; color: #2f3941;
    }
    .zd-hint { font-size: 12px; color: #87929d; margin-top: 10px; }

    .impact-card {
        background: #f0f6fc; border: 1px solid #d8e6f5;
        border-left: 3px solid #1f73b7; border-radius: 3px;
        padding: 12px 14px; margin-bottom: 12px; font-size: 13px;
        color: #2f3941; line-height: 1.55;
    }
    .impact-card .impact-title {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #1f73b7; margin-bottom: 6px;
    }
    .impact-card .impact-total {
        font-size: 13px; font-weight: 600; color: #03363d;
        margin-top: 6px; padding-top: 6px; border-top: 1px solid #d8e6f5;
    }
    .impact-card .impact-row { color: #49545c; }
    .impact-card .impact-source {
        font-size: 10px; color: #87929d; margin-top: 4px;
    }

    /* Detail view — Zendesk ticket layout */
    :root { --zd-detail-chrome: 268px; }
    .zd-detail-topbar {
        background: #fff; border-bottom: 1px solid #d8dcde;
        padding: 0 16px; min-height: 48px;
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 8px;
    }
    .zd-detail-tabs { display: flex; align-items: center; gap: 4px; }
    .zd-detail-tab {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 10px 12px; font-size: 13px; font-weight: 500; color: #2f3941;
        border-bottom: 2px solid #03363d; margin-bottom: -1px;
    }
    .zd-detail-tab-icon { color: #68737d; font-size: 14px; }
    .zd-detail-toolbar {
        display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    }
    .zd-detail-status {
        display: inline-block; padding: 4px 10px; border-radius: 3px;
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .zd-detail-status.badge-open { background: #cc3340; color: #fff; }
    .zd-detail-status.badge-pending { background: #1f73b7; color: #fff; }
    .zd-detail-status.badge-resolved { background: #038153; color: #fff; }
    .zd-detail-status.badge-closed { background: #87929d; color: #fff; }
    .zd-detail-status.badge-new { background: #ffc800; color: #2f3941; }
    .zd-detail-ticket-label { font-size: 13px; color: #2f3941; font-weight: 500; }
    .zd-detail-next {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 5px 12px; border: 1px solid #d8dcde; border-radius: 4px;
        background: #fff; color: #2f3941; font-size: 13px; cursor: default;
    }
    .zd-detail-inner { background: #f8f9f9; }

    .zd-props { padding: 14px 14px 0; background: #fff; font-size: 13px; min-width: 200px; }
    .zd-props-history {
        padding: 12px 14px 16px; background: #fff;
        border-top: 1px solid #d8dcde; font-size: 12px;
    }
    .zd-props-history .zd-history-header {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #68737d; margin: 0 0 8px;
    }
    .zd-props-history .zd-history-item {
        padding: 6px 8px; margin-bottom: 4px; gap: 6px;
    }
    .zd-props-history .zd-history-subj { font-size: 12px; -webkit-line-clamp: 2; }
    .zd-props-history .zd-history-meta { font-size: 10px; }
    .zd-prop { margin-bottom: 12px; }
    .zd-prop-label {
        font-size: 12px; color: #68737d; margin-bottom: 4px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .zd-prop-link { color: #1f73b7; font-size: 11px; cursor: default; }
    .zd-prop-select {
        display: flex; align-items: center; gap: 8px;
        padding: 6px 8px; border: 1px solid #d8dcde; border-radius: 3px;
        background: #fff; color: #2f3941; font-size: 13px; min-height: 32px;
    }
    .zd-prop-chev { margin-left: auto; color: #87929d; font-size: 10px; }
    .zd-prop-tags {
        display: flex; flex-wrap: wrap; gap: 4px;
        padding: 6px 8px; border: 1px solid #d8dcde; border-radius: 3px;
        background: #fff; min-height: 32px;
    }
    .zd-tag-chip-blue {
        display: inline-block; background: #e3f0fa; color: #1f73b7;
        padding: 2px 8px; border-radius: 3px; font-size: 11px;
    }
    .zd-avatar {
        display: inline-flex; align-items: center; justify-content: center;
        border-radius: 50%; color: #fff; font-size: 11px; font-weight: 600;
        flex-shrink: 0;
    }
    .zd-avatar-sm { width: 24px; height: 24px; }
    .zd-avatar-md { width: 36px; height: 36px; font-size: 13px; }
    .zd-avatar-lg { width: 48px; height: 48px; font-size: 16px; }

    .zd-conv-panel {
        display: flex; flex-direction: column;
        height: calc(100vh - var(--zd-detail-chrome, 268px));
        max-height: calc(100vh - var(--zd-detail-chrome, 268px));
        min-height: 0; background: #fff;
        overflow: hidden;
    }
    .zd-conv-header {
        padding: 12px 20px 8px; border-bottom: 1px solid #e9ebed;
        flex-shrink: 0;
    }
    .zd-conv-title { font-size: 18px; font-weight: 600; color: #2f3941; margin: 0; }
    .zd-conv-via {
        display: inline-block; font-size: 11px; color: #cc3340;
        margin-top: 4px;
    }
    .zd-conv-thread {
        flex: 1 1 auto; min-height: 0;
        padding: 12px 20px; overflow-y: auto;
        background: #fff;
    }
    .zd-msg-row {
        display: flex; gap: 10px; margin-bottom: 14px; align-items: flex-start;
    }
    .zd-msg-row.agent-row { margin-left: 34px; }
    .zd-msg-bubble {
        flex: 1; max-width: 85%; font-size: 13px; line-height: 1.55; color: #2f3941;
    }
    .zd-msg-bubble.customer {
        background: #e3f0f8; border: 1px solid #c5dff0;
        border-radius: 4px; padding: 10px 14px;
    }
    .zd-msg-bubble.internal {
        background: #fff3e0; border: 1px solid #f5dfc0;
        border-radius: 4px; padding: 10px 14px;
    }
    .zd-msg-bubble.agent { padding: 4px 0; }
    .zd-msg-bubble.agent-public {
        background: #f3f4f4; border: 1px solid #e9ebed;
        border-radius: 4px; padding: 10px 14px;
    }
    .zd-msg-sender { font-size: 12px; color: #68737d; margin-bottom: 4px; }
    .zd-msg-sender strong { color: #2f3941; font-weight: 600; }
    .zd-internal-badge {
        display: inline-block; font-size: 9px; font-weight: 700;
        text-transform: uppercase; color: #b35a00;
        background: #ffe8cc; padding: 1px 5px; border-radius: 2px;
        margin-left: 6px; vertical-align: middle;
    }
    .zd-composer {
        border-top: 1px solid #d8dcde; padding: 10px 16px 12px;
        background: #fff;
        flex-shrink: 0;
    }
    .zd-composer-tabs {
        display: flex; gap: 16px; margin-bottom: 8px;
        font-size: 12px; color: #68737d;
    }
    .zd-composer-tab.active {
        color: #2f3941; font-weight: 600;
        border-bottom: 2px solid #03363d; padding-bottom: 4px;
    }
    .zd-composer-to { font-size: 12px; color: #68737d; margin-bottom: 8px; }
    .zd-composer-input {
        border: 1px solid #d8dcde; border-radius: 4px;
        min-height: 64px; padding: 10px 12px;
        background: #fff; color: #87929d; font-size: 13px;
    }
    .zd-composer-toolbar {
        display: flex; gap: 12px; margin-top: 8px; color: #68737d; font-size: 14px;
    }

    .zd-context { padding: 12px; font-size: 13px; overflow-y: auto; }
    .zd-context-profile {
        background: #fff; border: 1px solid #d8dcde; border-radius: 4px;
        padding: 14px; margin-bottom: 12px;
    }
    .zd-context-profile-top {
        display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
    }
    .zd-context-name { font-size: 14px; font-weight: 600; color: #2f3941; }
    .zd-context-row {
        font-size: 12px; color: #49545c; margin-bottom: 5px; line-height: 1.4;
    }
    .zd-context-row .lbl { color: #68737d; }
    .zd-context-row a { color: #1f73b7; text-decoration: none; }
    .zd-context-row a:hover { text-decoration: underline; }
    .zd-context-notes {
        background: #f8f9f9; border: 1px solid #e9ebed; border-radius: 3px;
        padding: 8px 10px; font-size: 12px; color: #49545c; margin-top: 8px;
    }
    .zd-context-org {
        background: #fff; border: 1px solid #d8dcde; border-radius: 4px;
        padding: 12px; margin-bottom: 0;
    }
    .zd-context-org-title {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #68737d; margin-bottom: 8px;
    }
    .zd-history-header {
        display: flex; align-items: center; justify-content: space-between;
        font-size: 12px; font-weight: 600; color: #2f3941;
        margin: 4px 0 8px;
    }
    .zd-history-icons { color: #68737d; font-size: 13px; display: flex; gap: 8px; }
    .zd-history-item {
        display: flex; gap: 8px; align-items: flex-start;
        padding: 8px 10px; border: 1px solid #e9ebed; border-radius: 3px;
        margin-bottom: 6px; font-size: 12px; background: #fff;
    }
    .zd-history-item.active { background: #e3f0f8; border-color: #b8d4f0; }
    .zd-history-subj {
        font-weight: 500; color: #2f3941; line-height: 1.35;
        overflow: hidden; text-overflow: ellipsis;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    }
    .zd-history-meta { font-size: 11px; color: #68737d; margin-top: 3px; }
    .zd-apps-strip {
        width: 40px; min-width: 40px; background: #fff;
        border-left: 1px solid #d8dcde;
        display: flex; flex-direction: column; align-items: center;
        padding: 8px 0; gap: 4px;
    }
    .zd-apps-icon {
        width: 32px; height: 32px; border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        color: #68737d; font-size: 16px;
    }
    .zd-apps-icon.active { background: #e9f2f9; color: #1f73b7; }
    .zd-back-link { color: #1f73b7; font-size: 12px; cursor: pointer; text-decoration: none; }
    .zd-back-link:hover { text-decoration: underline; }

    .zd-demo-item {
        display: block; padding: 5px 16px;
        font-size: 12px; color: #49545c; text-decoration: none !important; line-height: 1.4;
    }
    .zd-demo-item:visited, .zd-demo-item:link { color: #49545c; text-decoration: none !important; }
    .zd-demo-item:hover { background: #f3f4f4; color: #2f3941; text-decoration: none !important; }
    div[data-testid="stHorizontalBlock"] .zd-sim-btn button {
        background: transparent !important; border: none !important;
        color: #1f73b7 !important; font-size: 12px !important;
        padding: 0 !important; box-shadow: none !important;
        min-height: 0 !important; text-decoration: underline !important;
    }
    .stButton > button[kind="primary"] {
        background: #03363d !important; border-color: #03363d !important;
        font-size: 13px !important; font-weight: 500 !important;
        border-radius: 4px !important; padding: 7px 16px !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #17494d !important; border-color: #17494d !important;
    }
    .stButton > button[kind="secondary"] {
        background: #fff !important; border-color: #d8dcde !important;
        color: #2f3941 !important; font-size: 12px !important;
    }
    body.zd-detail-mode .st-key-back_to_list .stButton > button {
        background: transparent !important; border: none !important;
        color: #1f73b7 !important; font-size: 12px !important;
        padding: 8px 16px !important; box-shadow: none !important;
        min-height: 0 !important; text-align: left !important;
    }
    [data-testid="stExpander"] { font-size: 12px !important; }
    [data-testid="stCaptionContainer"] { font-size: 11px !important; color: #87929d !important; }
</style>
"""


st.set_page_config(
    page_title="Zendesk — Tickets",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(ZENDESK_CSS, unsafe_allow_html=True)
st.markdown(JIRA_CSS, unsafe_allow_html=True)


def synthetic_requester_name(ticket_id: str) -> str:
    return REQUESTER_NAMES[hash(ticket_id) % len(REQUESTER_NAMES)]


def synthetic_channel(ticket_id: str) -> str:
    return CHANNELS[hash(ticket_id + "_ch") % len(CHANNELS)]


def synthetic_assignee(ticket_id: str) -> str:
    return AGENT_NAMES[hash(ticket_id + "_ag") % len(AGENT_NAMES)]


def synthetic_ticket_form(category: str) -> str:
    return FORM_LABELS.get(category, "Default Ticket Form")


# Zendesk-style ticket type: Issue (broken/not working) vs Request (customer action).
TYPE_ISSUE_CATEGORIES = {"technical", "api"}
TYPE_REQUEST_CATEGORIES = {"billing", "upgrade", "cancellation", "complaint"}


def ticket_type_label(category: str) -> str:
    cat = (category or "").lower()
    if cat in TYPE_ISSUE_CATEGORIES:
        return "Issue"
    if cat in TYPE_REQUEST_CATEGORIES:
        return "Request"
    return "Issue"  # default for unknown categories


def priority_label(priority: str) -> str:
    return PRIORITY_LABELS.get(priority.lower(), priority.replace("_", " ").title())


def avatar_initials(name: str) -> str:
    parts = name.replace("/", " ").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


AVATAR_COLORS = [
    "#1f73b7", "#038153", "#cc3340", "#6f42c1", "#e67e22",
    "#16a085", "#2c3e50", "#c0392b", "#8e44ad", "#2980b9",
]


def avatar_color(name: str) -> str:
    return AVATAR_COLORS[hash(name) % len(AVATAR_COLORS)]


def avatar_html(name: str, size: str = "sm") -> str:
    cls = f"zd-avatar zd-avatar-{size}"
    bg = avatar_color(name)
    return (
        f'<span class="{cls}" style="background:{bg};">'
        f"{html.escape(avatar_initials(name))}</span>"
    )


def synthetic_phone(ticket_id: str) -> str:
    n = abs(hash(ticket_id + "_ph")) % 9000000 + 1000000
    return f"+1 408 {n // 10000} {n % 10000:04d}"


def format_local_time(created_at: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%a, %H:%M UTC")
    except (ValueError, AttributeError):
        return "—"


def customer_note(ticket: dict) -> str:
    tier = (ticket.get("account_tier") or ticket.get("customer_tier") or "free").lower()
    company = ticket.get("account_name") or "this account"
    if tier == "enterprise":
        return f"Valuable Customer since 2010 — {company} enterprise account"
    if tier == "pro":
        return f"Pro customer — {company} since 2018"
    return f"Customer since 2022 — {company}"


def internal_note_text(ticket: dict) -> str:
    tier = (ticket.get("account_tier") or ticket.get("customer_tier") or "free").lower()
    name = ticket.get("requester_name", "Customer")
    if tier == "enterprise":
        return f"{name} is on an enterprise account — prioritize response."
    if tier == "pro":
        return f"{name} is a pro customer. Give attentive support."
    return f"Standard support tier for {name}."


def agent_reply_text(ticket: dict) -> str:
    name = ticket.get("requester_name", "").split()[0]
    subject = ticket.get("subject", "")
    if "api" in ticket.get("category", "").lower():
        return (
            f"Hi {name}, thanks for reaching out. "
            f"I can help with your API question. Let me review your account setup."
        )
    return (
        f"Hi {name}, how can I help you today? "
        f"I see your request about: {truncate(subject, 60)}"
    )


def channel_via_label(channel: str) -> str:
    if channel == "API":
        return "Via API"
    return f"Via {channel.lower()}"


@st.cache_data
def get_interaction_history(ticket_id: str, account_id: str | None, limit: int = 3) -> list[dict]:
    if not account_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, subject, status, created_at FROM tickets "
        "WHERE account_id = ? AND id != ? ORDER BY created_at DESC LIMIT ?",
        (account_id, ticket_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def status_icon_html(status: str) -> str:
    mapping = {
        "open": ("O", "status-open"),
        "pending": ("P", "status-pending"),
        "resolved": ("S", "status-resolved"),
        "closed": ("C", "status-closed"),
        "new": ("N", "status-new"),
    }
    letter, css = mapping.get(status, ("?", "status-closed"))
    return f'<span class="status-sq {css}">{letter}</span>'


def status_badge_class(status: str) -> str:
    return {
        "open": "badge-open",
        "pending": "badge-pending",
        "resolved": "badge-resolved",
        "closed": "badge-closed",
        "new": "badge-new",
    }.get(status, "badge-closed")


def status_label_html(status: str) -> str:
    label = status.capitalize() if status else "—"
    badge_cls = status_badge_class(status)
    return f'<span class="status-badge {badge_cls}">{html.escape(label)}</span>'


def format_date(created_at: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except (ValueError, AttributeError):
        return str(created_at)[:10] if created_at else "—"


def truncate(text: str, length: int = 52) -> str:
    return text if len(text) <= length else text[: length - 1] + "…"


def parse_tags(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def ticket_select_columns(conn: sqlite3.Connection) -> str:
    """Select v2 identity fields while remaining compatible with the legacy DB."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    optional = [
        name if name in columns else f"NULL AS {name}"
        for name in ("requester_name", "channel", "assignee")
    ]
    return (
        "id, created_at, subject, body, category, priority, status, "
        "customer_tier, tags, cluster, requester_email, account_id, "
        + ", ".join(optional)
    )


@st.cache_data
def get_accounts_indexes() -> tuple[dict[str, dict], dict[str, dict]]:
    accounts = load_accounts()
    by_email = {
        a["customer_email"]: a
        for a in accounts.values()
        if a.get("customer_email")
    }
    return accounts, by_email


def lookup_account(ticket: dict) -> dict | None:
    by_id, by_email = get_accounts_indexes()
    account_id = ticket.get("account_id")
    if account_id and account_id in by_id:
        return by_id[account_id]
    email = ticket.get("requester_email")
    if email and email in by_email:
        return by_email[email]
    return None


def enrich_ticket(ticket: dict) -> dict:
    ticket["tags"] = parse_tags(ticket.get("tags"))
    account = lookup_account(ticket)
    if account:
        ticket["account_name"] = account.get("account_name", "")
        ticket["account_arr"] = account.get("arr", 0)
        ticket["account_arr_formatted"] = format_arr(account.get("arr", 0))
        ticket["account_region"] = account.get("region", "")
        ticket["account_tier"] = account.get("tier", ticket.get("customer_tier", ""))
    else:
        ticket["account_name"] = ""
        ticket["account_arr"] = 0
        ticket["account_arr_formatted"] = "—"
        ticket["account_region"] = ""
        ticket["account_tier"] = ticket.get("customer_tier", "")
    return ticket


@st.cache_data
def load_conversations_index() -> dict[str, list[dict]]:
    if not CONVERSATIONS_PATH.exists():
        return {}
    with open(CONVERSATIONS_PATH, encoding="utf-8") as f:
        threads = json.load(f)
    return {t["ticket_id"]: t["messages"] for t in threads}


def get_ticket_messages(ticket: dict) -> list[dict]:
    messages = load_conversations_index().get(ticket["id"])
    if messages:
        return messages
    return [{
        "author": "customer",
        "name": ticket.get("requester_name", "Customer"),
        "text": ticket.get("body", ""),
        "timestamp": ticket.get("created_at", ""),
        "type": "public",
    }]


def format_message_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except (ValueError, AttributeError):
        return str(ts)[:16] if ts else "—"


def render_conversation_thread_html(messages: list[dict]) -> str:
    rows = []
    for msg in messages:
        name = html.escape(msg.get("name", ""))
        text = html.escape(msg.get("text", ""))
        ts = html.escape(format_message_ts(msg.get("timestamp", "")))
        author = msg.get("author", "customer")
        msg_type = msg.get("type", "public")
        av = avatar_html(msg.get("name", ""), "md")

        if msg_type == "internal":
            rows.append(
                f'<div class="zd-msg-row">{av}'
                f'<div class="zd-msg-bubble internal">'
                f'<div class="zd-msg-sender"><strong>{name}</strong>'
                f'<span class="zd-internal-badge">Internal</span></div>{text}</div></div>'
            )
        elif author == "customer":
            rows.append(
                f'<div class="zd-msg-row">{av}'
                f'<div class="zd-msg-bubble customer">'
                f'<div class="zd-msg-sender"><strong>{name}</strong> &middot; {ts}</div>'
                f"{text}</div></div>"
            )
        else:
            rows.append(
                f'<div class="zd-msg-row agent-row">{av}'
                f'<div class="zd-msg-bubble agent-public">'
                f'<div class="zd-msg-sender"><strong>{name}</strong> &middot; {ts}</div>'
                f"{text}</div></div>"
            )

    return f'<div class="zd-conv-thread">{"".join(rows)}</div>'


def get_latest_comment(ticket: dict) -> dict | None:
    messages = get_ticket_messages(ticket)
    if not messages:
        return None
    for msg in reversed(messages):
        if msg.get("type") != "internal":
            return msg
    return messages[-1]


def render_hover_popup_html(ticket: dict) -> str:
    status_upper = ticket["status"].upper()
    badge_cls = status_badge_class(ticket["status"])
    tid = html.escape(ticket["id"])
    subject = html.escape(ticket["subject"])
    body_preview = html.escape(truncate(ticket.get("body", ""), 140))
    requester = html.escape(ticket.get("requester_name", ""))
    channel = html.escape(ticket.get("channel", ""))

    latest = get_latest_comment(ticket)
    latest_html = ""
    if latest:
        author = html.escape(latest.get("name", ""))
        date_str = html.escape(format_date(latest.get("timestamp", "")))
        text = html.escape(truncate(latest.get("text", ""), 160))
        latest_html = (
            f'<div class="zd-hover-latest-label">Latest comment</div>'
            f'<div class="zd-hover-latest-header">'
            f"<strong>{author}</strong><span>{date_str}</span></div>"
            f'<div class="zd-hover-latest-text">{text}</div>'
        )

    return (
        f'<div class="zd-hover-popup">'
        f'<div class="zd-hover-top">'
        f'<span class="zd-hover-badge {badge_cls}">{status_upper}</span>'
        f'<span class="zd-hover-id">Ticket #{tid}</span></div>'
        f'<div class="zd-hover-subject">{subject}</div>'
        f'<div class="zd-hover-body">{body_preview}</div>'
        f"{latest_html}"
        f'<div class="zd-hover-meta">{requester} &middot; {channel}</div>'
        f"</div>"
    )


def current_view_label(category: str) -> str:
    if category == "All":
        return "All tickets"
    return VIEW_LABELS.get(category, category.replace("_", " ").title())


@st.cache_data
def get_category_counts() -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT category, COUNT(*) AS cnt FROM tickets GROUP BY category ORDER BY category"
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


@st.cache_data
def get_total_ticket_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    conn.close()
    return count


@st.cache_data
def get_unsolved_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'pending')"
    ).fetchone()[0]
    conn.close()
    return count


@st.cache_data
def get_unassigned_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    if "assignee" in columns:
        count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'open' "
            "AND (assignee IS NULL OR assignee = '' OR assignee = '—')"
        ).fetchone()[0]
        conn.close()
        return count
    rows = conn.execute("SELECT id FROM tickets WHERE status = 'open'").fetchall()
    conn.close()
    return sum(1 for (tid,) in rows if synthetic_assignee(tid) == "—")


@st.cache_data
def get_open_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE status = 'open'"
    ).fetchone()[0]
    conn.close()
    return count


def _ticket_matches_search(row: sqlite3.Row | dict, search: str) -> bool:
    q = search.strip().lower()
    if not q:
        return True
    ticket_id = row["id"]
    requester_name = row["requester_name"] if "requester_name" in row.keys() else None
    fields = (
        str(ticket_id),
        row["subject"],
        row["body"],
        row["requester_email"] or "",
        requester_name or synthetic_requester_name(ticket_id),
    )
    return any(q in str(field).lower() for field in fields)


def list_tickets(
    category: str = "All",
    search: str = "",
    page: int = 0,
    page_size: int = PAGE_SIZE,
) -> tuple[list[dict], int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where_clauses: list[str] = []
    params: list = []

    if category == "unsolved":
        where_clauses.append("status IN ('open', 'pending')")
    elif category == "unassigned":
        where_clauses.append("status = 'open'")
    elif category == "open":
        where_clauses.append("status = 'open'")
    elif category != "All":
        where_clauses.append("category = ?")
        params.append(category)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    offset = page * page_size
    search_active = bool(search.strip())
    needs_full_fetch = category == "unassigned" or search_active

    if needs_full_fetch:
        rows = conn.execute(
            f"SELECT {ticket_select_columns(conn)} "
            f"FROM tickets {where_sql} ORDER BY created_at DESC",
            params,
        ).fetchall()
        conn.close()
        filtered = [dict(row) for row in rows]
        if category == "unassigned":
            filtered = [
                t for t in filtered
                if (t.get("assignee") or synthetic_assignee(t["id"])) == "—"
            ]
        if search_active:
            filtered = [t for t in filtered if _ticket_matches_search(t, search)]
        total = len(filtered)
        page_rows = filtered[offset : offset + page_size]
    else:
        total = conn.execute(
            f"SELECT COUNT(*) FROM tickets {where_sql}", params
        ).fetchone()[0]
        page_rows = [
            dict(row)
            for row in conn.execute(
                f"SELECT {ticket_select_columns(conn)} "
                f"FROM tickets {where_sql} "
                f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()
        ]
        conn.close()

    tickets = []
    for t in page_rows:
        enrich_ticket(t)
        t["requester_name"] = t.get("requester_name") or synthetic_requester_name(t["id"])
        t["channel"] = t.get("channel") or synthetic_channel(t["id"])
        t["assignee"] = t.get("assignee") or synthetic_assignee(t["id"])
        t["ticket_form"] = synthetic_ticket_form(t["category"])
        tickets.append(t)
    return tickets, total


@st.cache_resource(show_spinner="Loading embeddings (first run may take a minute)...")
def get_cache():
    return compute_embeddings()


@st.cache_data(show_spinner=False)
def get_trend_signals(ticket_ids: tuple[str, ...]) -> dict[str, dict]:
    return detect_trends_batch(get_cache(), ticket_ids)


@st.cache_data
def get_ticket_details(ticket_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT {ticket_select_columns(conn)} FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    ticket = enrich_ticket(dict(row))
    ticket["requester_name"] = ticket.get("requester_name") or synthetic_requester_name(ticket_id)
    ticket["channel"] = ticket.get("channel") or synthetic_channel(ticket_id)
    ticket["assignee"] = ticket.get("assignee") or synthetic_assignee(ticket_id)
    ticket["ticket_form"] = synthetic_ticket_form(ticket["category"])
    return ticket


def load_demo_scenarios() -> list[dict]:
    with open(DEMO_PATH, encoding="utf-8") as f:
        return json.load(f)["scenarios"]


def run_analysis(ticket_id: str):
    cache = get_cache()
    similar = find_similar(cache, ticket_id, top_k=5)
    trend = detect_trend(cache, ticket_id)
    impact = calculate_customer_impact(trend["similar_ids"], ticket_id)
    return similar, trend, impact


def copy_button(text: str, button_id: str):
    payload = json.dumps(text)
    components.html(
        f"""
        <button id="{button_id}" style="padding:6px 14px;cursor:pointer;border-radius:4px;
            border:1px solid #03363d;background:#03363d;color:#fff;font-size:12px;
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
          Copy to clipboard
        </button>
        <script>
          document.getElementById("{button_id}").onclick = () => {{
            navigator.clipboard.writeText({payload});
            document.getElementById("{button_id}").textContent = "Copied";
            setTimeout(() => {{
              document.getElementById("{button_id}").textContent = "Copy to clipboard";
            }}, 1500);
          }};
        </script>
        """,
        height=40,
    )


def _qp_value(qp, key: str) -> str | None:
    """Return a single query-param value (Streamlit may expose str or list)."""
    if key not in qp:
        return None
    value = qp[key]
    if isinstance(value, list):
        return value[0] if value else None
    return str(value)


def sync_query_params():
    qp = st.query_params
    ticket = _qp_value(qp, "ticket")
    if ticket:
        st.session_state.selected_ticket_id = ticket
        st.session_state.pop("results", None)
    view = _qp_value(qp, "view")
    if view:
        st.session_state.category_filter = view
        st.session_state.list_page = 0
        st.session_state.page_mode = "list"
    page = _qp_value(qp, "page")
    if page is not None:
        try:
            st.session_state.list_page = max(0, int(page))
        except ValueError:
            pass
    mode = _qp_value(qp, "mode")
    if mode == "jira":
        issue = _qp_value(qp, "issue")
        if issue:
            st.session_state.jira_issue = issue
        else:
            st.session_state.pop("jira_issue", None)
        jira_filter = _qp_value(qp, "filter")
        if jira_filter:
            st.session_state.jira_filter = jira_filter
        elif not issue:
            st.session_state.jira_filter = "all"
        jira_nav = _qp_value(qp, "nav")
        if jira_nav:
            st.session_state.jira_nav = jira_nav
        elif not issue:
            st.session_state.jira_nav = "backlog"
    else:
        issue = _qp_value(qp, "issue")
        if issue:
            st.session_state.jira_issue = issue
        elif "issue" in qp:
            st.session_state.pop("jira_issue", None)
        jira_filter = _qp_value(qp, "filter")
        if jira_filter:
            st.session_state.jira_filter = jira_filter
    jira_search = _qp_value(qp, "jira_search")
    if jira_search is not None:
        st.session_state.jira_search = jira_search
    elif "jira_search" in qp:
        st.session_state.pop("jira_search", None)
    jira_page = _qp_value(qp, "jira_page")
    if jira_page is not None:
        try:
            st.session_state.jira_page = max(0, int(jira_page))
        except ValueError:
            pass
    elif "jira_page" in qp:
        st.session_state.jira_page = 0
    if "search" in qp and mode != "jira":
        st.session_state.search_query = _qp_value(qp, "search") or ""
        st.session_state.header_search = st.session_state.search_query
        st.session_state._applied_search_query = st.session_state.search_query
        st.session_state.list_page = 0
        if mode != "detail":
            st.session_state.page_mode = "list"
    if mode:
        st.session_state.page_mode = mode
    analyze = _qp_value(qp, "analyze")
    if analyze == "1":
        ticket = _qp_value(qp, "ticket") or st.session_state.get("selected_ticket_id")
        if ticket:
            st.session_state["_analyze_requested"] = ticket
        st.query_params.pop("analyze", None)
    create_jira = _qp_value(qp, "create_jira")
    create = _qp_value(qp, "create")
    if create_jira == "1":
        ticket = _qp_value(qp, "ticket") or st.session_state.get("selected_ticket_id")
        if ticket:
            st.session_state["_create_jira_requested"] = ticket
            return_mode = mode if mode in ("detail", "trend") else "detail"
            st.session_state["_jira_create_return"] = {
                "mode": return_mode,
                "ticket": ticket,
            }
        st.query_params.pop("create_jira", None)
    elif create == "1":
        ticket = _qp_value(qp, "ticket") or st.session_state.get("selected_ticket_id")
        if ticket and "_jira_create_draft" not in st.session_state:
            st.session_state["_create_jira_requested"] = ticket
            if "_jira_create_return" not in st.session_state:
                st.session_state["_jira_create_return"] = {
                    "mode": "detail",
                    "ticket": ticket,
                }


def set_query_params(**kwargs):
    """Update URL query params and keep session state in sync."""
    for key, value in kwargs.items():
        if value is None:
            st.query_params.pop(key, None)
        else:
            st.query_params[key] = str(value)


def back_to_ticket_list():
    st.session_state.page_mode = "list"
    set_query_params(mode="list")


def install_query_param_navigation():
    """Streamlit rewrites markdown links (target=_blank) and strips onclick."""
    components.html(
        """
        <script>
        (function () {
          const parentWin = window.parent;
          if (parentWin.__zdNavInstalled) return;
          parentWin.__zdNavInstalled = true;

          const script = parentWin.document.createElement("script");
          script.textContent = `
            (function () {
              const navigate = (href) => {
                const qs = href.startsWith("?") ? href.slice(1) : href;
                const url = new URL(window.location.href);
                url.search = qs ? "?" + qs : "";
                window.location.assign(url.toString());
              };

              document.body.addEventListener(
                "click",
                (event) => {
                  const link = event.target.closest('a[href^="?"]');
                  if (link) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    navigate(link.getAttribute("href"));
                    return;
                  }
                  const analyzeBtn = event.target.closest(".zd-analyze-btn");
                  if (analyzeBtn) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    const ticket = analyzeBtn.getAttribute("data-ticket");
                    if (!ticket) return;
                    const url = new URL(window.location.href);
                    url.searchParams.set("ticket", ticket);
                    url.searchParams.set("mode", "detail");
                    url.searchParams.set("analyze", "1");
                    window.location.assign(url.toString());
                    return;
                  }
                  const row = event.target.closest("tr.zd-row[data-ticket]");
                  if (row && !event.target.closest("a")) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    const ticket = row.getAttribute("data-ticket");
                    if (!ticket) return;
                    const url = new URL(window.location.href);
                    url.searchParams.set("ticket", ticket);
                    url.searchParams.set("mode", "detail");
                    window.location.assign(url.toString());
                  }
                },
                true,
              );

              let activePopup = null;
              const positionPopup = (row) => {
                const popup = row.querySelector(".zd-hover-popup");
                if (!popup) return;
                if (activePopup && activePopup !== popup) {
                  activePopup.classList.remove("visible");
                }
                const rect = row.getBoundingClientRect();
                const popupW = 400;
                let left = rect.left + 100;
                if (left + popupW > window.innerWidth - 16) {
                  left = window.innerWidth - popupW - 16;
                }
                if (left < 16) left = 16;
                let top = rect.top;
                if (top + 280 > window.innerHeight - 8) {
                  top = Math.max(8, rect.bottom - 280);
                }
                popup.style.left = left + "px";
                popup.style.top = top + "px";
                popup.classList.add("visible");
                activePopup = popup;
              };
              const hidePopup = (row) => {
                const popup = row && row.querySelector(".zd-hover-popup");
                if (popup) {
                  popup.classList.remove("visible");
                  if (activePopup === popup) activePopup = null;
                }
              };

              document.body.addEventListener(
                "mouseover",
                (event) => {
                  const row = event.target.closest("tr.zd-row[data-ticket]");
                  if (row) positionPopup(row);
                },
                true,
              );
              document.body.addEventListener(
                "mouseout",
                (event) => {
                  const row = event.target.closest("tr.zd-row[data-ticket]");
                  if (row && !row.contains(event.relatedTarget)) hidePopup(row);
                },
                true,
              );

              const stripTargets = () => {
                document.querySelectorAll('a[href^="?"][target]').forEach((link) => {
                  link.removeAttribute("target");
                });
              };
              stripTargets();
              if (document.body) {
                new MutationObserver(stripTargets).observe(document.body, {
                  childList: true,
                  subtree: true,
                });
              }
            })();
          `;
          parentWin.document.head.appendChild(script);
        })();
        </script>
        """,
        height=0,
    )


def init_session_state(scenarios: list[dict]):
    if "selected_ticket_id" not in st.session_state:
        st.session_state.selected_ticket_id = scenarios[0]["ticket_id"]
    if "list_page" not in st.session_state:
        st.session_state.list_page = 0
    if "category_filter" not in st.session_state:
        st.session_state.category_filter = "All"
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "header_search" not in st.session_state:
        st.session_state.header_search = st.session_state.search_query
    if "_applied_search_query" not in st.session_state:
        st.session_state._applied_search_query = st.session_state.search_query
    if "page_mode" not in st.session_state:
        st.session_state.page_mode = "list"
    if "jira_filter" not in st.session_state:
        st.session_state.jira_filter = "all"
    if "jira_nav" not in st.session_state:
        st.session_state.jira_nav = "backlog"
    if "jira_search" not in st.session_state:
        st.session_state.jira_search = ""
    if "jira_page" not in st.session_state:
        st.session_state.jira_page = 0


def select_ticket(ticket_id: str):
    st.session_state.selected_ticket_id = ticket_id
    st.session_state.pop("results", None)


def render_global_header():
    col_spacer, col_search, col_icons = st.columns([0.52, 0.20, 0.28], gap="small")

    with col_spacer:
        st.empty()

    with col_search:
        with st.form("header_search_form", clear_on_submit=False, border=False):
            q = st.text_input(
                "Search",
                key="header_search",
                label_visibility="collapsed",
                placeholder="Search",
            )
            submitted = st.form_submit_button("Search")

        if submitted:
            query = q.strip()
            st.session_state.search_query = query
            st.session_state._applied_search_query = query
            st.session_state.list_page = 0
            st.session_state.page_mode = "list"
            set_query_params(mode="list", page="0", search=query or None, ticket=None)

    with col_icons:
        st.markdown(
            f"""
            <div class="zd-global-icons">
                <div class="zd-icon-btn" title="Chat">{SVG_CHAT_OUTLINE}</div>
                <div class="zd-icon-btn" title="Phone">{SVG_PHONE}</div>
                <div class="zd-icon-filled" title="Customer context">{SVG_USER_FILLED}</div>
                <div class="zd-icon-filled" title="Talk">{SVG_TALK_FILLED}</div>
                <div class="zd-icon-filled" title="Messaging">
                    {SVG_MSG_FILLED}<span class="zd-notify-dot"></span>
                </div>
                <div class="zd-icon-btn" title="Apps">{SVG_GRID}</div>
                <div class="zd-profile-initials" title="Agent profile">KY</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_tab_bar(tab_label: str):
    st.markdown(
        f"""
        <div class="zd-tab-bar">
            <div class="zd-tab-add">+ Add</div>
            <div class="zd-tab-chip">
                <span>{html.escape(tab_label)}</span>
                <span class="zd-tab-close" title="Close tab">{SVG_CLOSE}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_icon_nav():
    st.markdown(
        f"""
        <div class="zd-icon-nav">
            <div class="zd-icon" title="Home">{SVG_HOME}</div>
            <div class="zd-icon active" title="Tickets">{SVG_TICKET}</div>
            <div class="zd-icon" title="Customers">{SVG_USERS}</div>
            <a class="zd-icon" href="{trend_dashboard_url()}" title="Trend Detection Dashboard">{SVG_CHART}</a>
            <a class="zd-icon" href="?mode=jira" title="Jira">{SVG_JIRA}</a>
            <div class="zd-icon" title="Settings">{SVG_GEAR}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_views_sidebar(
    category_counts: dict[str, int],
    total: int,
    unsolved: int,
    unassigned: int,
    open_count: int,
    scenarios: list[dict],
):
    current = st.session_state.category_filter

    view_items = [
        ("unsolved", VIEW_LABELS["unsolved"], unsolved),
        ("unassigned", VIEW_LABELS["unassigned"], unassigned),
        ("All", "All tickets", total),
        ("open", VIEW_LABELS["open"], open_count),
    ]
    for cat in VIEW_ORDER:
        if cat in category_counts:
            view_items.append((cat, VIEW_LABELS[cat], category_counts[cat]))

    items_html = []
    for key, label, count in view_items:
        active = " active" if current == key else ""
        href = f"?view={html.escape(key, quote=True)}"
        items_html.append(
            f'<a class="zd-view-item{active}" href="{href}">'
            f'<span class="zd-view-name">{html.escape(label)}</span>'
            f'<span class="zd-view-count">{count:,}</span>'
            f"</a>"
        )

    demo_html = []
    for scenario in scenarios:
        tid = scenario["ticket_id"]
        cat = scenario.get("category", "All")
        short = truncate(scenario["label"], 42)
        href = (
            f"?ticket={html.escape(tid, quote=True)}"
            f"&view={html.escape(cat, quote=True)}"
            f"&mode=detail"
        )
        demo_html.append(
            f'<a class="zd-demo-item" href="{href}">'
            f"{html.escape(short)} ({html.escape(tid)})</a>"
        )

    st.markdown(
        f"""
        <div class="zd-views">
            <div class="zd-views-top">
                <div class="zd-views-header">Views</div>
                <div class="zd-views-actions">
                    <span title="Refresh">&#8635;</span>
                    <span title="Collapse">&#8250;</span>
                </div>
            </div>
            {"".join(items_html)}
            <div class="zd-views-divider"></div>
            <div class="zd-demo-section">
                <div class="zd-demo-label">Suggested for demo</div>
                {"".join(demo_html)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_view_header(total_filtered: int):
    view_name = current_view_label(st.session_state.category_filter)
    st.markdown(
        f"""
        <div class="zd-view-header">
            <div class="zd-view-header-left">
                <div class="zd-view-title-row">
                    {SVG_VIEW_BOX}
                    <span class="zd-view-title">{html.escape(view_name)}</span>
                </div>
                <div class="zd-view-subtitle">{total_filtered:,} tickets</div>
            </div>
            <div class="zd-play-btn" title="Play view (demo)">{SVG_PLAY} Play</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _page_numbers(current: int, total_pages: int, window: int = 5) -> list:
    if total_pages <= window + 2:
        return list(range(total_pages))
    pages = set()
    pages.update(range(max(0, current - 1), min(total_pages, current + 2)))
    pages.add(0)
    pages.add(total_pages - 1)
    return sorted(pages)


def render_ticket_table(tickets: list[dict], total: int, page: int):
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    rows_html = []
    for t in tickets:
        trend_signal = t.get("trend_signal", {})
        has_warning = bool(trend_signal.get("is_potential_trend"))
        row_class = "zd-row zd-row-trend" if has_warning else "zd-row"
        warning_html = ""
        if has_warning:
            similar_count = int(trend_signal.get("similar_count", 0))
            warning_html = (
                '<span class="zd-trend-warning" '
                f'title="{similar_count} similar tickets found">'
                f'&#9888; Potential trend ({similar_count})</span>'
            )
        tid = html.escape(t["id"])
        ticket_href = (
            f"?ticket={html.escape(t['id'], quote=True)}&mode=detail"
        )
        popup_html = render_hover_popup_html(t)
        rows_html.append(
            f'<tr class="{row_class}" data-ticket="{tid}">'
            f'<td class="col-check"><span class="chk">&#9744;</span></td>'
            f'<td class="col-status">{status_icon_html(t["status"])}</td>'
            f'<td class="col-status-label">{status_label_html(t["status"])}</td>'
            f'<td class="col-id"><a href="{ticket_href}">{tid}</a></td>'
            f'<td class="col-subject" title="{html.escape(t["subject"])}">'
            f"{popup_html}"
            f'<a class="subj-link" href="{ticket_href}">'
            f"{html.escape(truncate(t['subject'], 36))}</a>{warning_html}</td>"
            f'<td class="col-channel">{html.escape(t["channel"])}</td>'
            f'<td class="col-requester">{html.escape(t["requester_name"])}</td>'
            f'<td class="col-date">{html.escape(format_date(t["created_at"]))}</td>'
            f'<td class="col-assignee">{html.escape(t["assignee"])}</td>'
            f"</tr>"
        )

    page_links = []
    shown = _page_numbers(page, total_pages)
    prev_p = -1
    for p in shown:
        if prev_p >= 0 and p - prev_p > 1:
            page_links.append('<span class="zd-page-num disabled">…</span>')
        cls = "zd-page-num active" if p == page else "zd-page-num"
        page_links.append(f'<a class="{cls}" href="?page={p}">{p + 1}</a>')
        prev_p = p

    prev_cls = "zd-page-num" if page > 0 else "zd-page-num disabled"
    next_cls = "zd-page-num" if page < total_pages - 1 else "zd-page-num disabled"
    prev_href = f"?page={page - 1}" if page > 0 else "#"
    next_href = f"?page={page + 1}" if page < total_pages - 1 else "#"

    st.markdown(
        f"""
        <div class="zd-table-wrap">
        <table class="zd-table">
        <thead><tr>
            <th class="col-check">&#9744;</th>
            <th class="col-status"></th>
            <th class="col-status-label">Status</th>
            <th class="col-id">ID</th>
            <th class="col-subject">Subject</th>
            <th class="col-channel">Channel</th>
            <th class="col-requester">Requester</th>
            <th class="col-date">Requested &#9660;</th>
            <th class="col-assignee">Assignee</th>
        </tr></thead>
        <tbody>{"".join(rows_html)}</tbody>
        </table>
        <div class="zd-pagination">
            <span>{total:,} tickets</span>
            <div class="zd-page-nums">
                <a class="{prev_cls}" href="{prev_href}">&lsaquo;</a>
                {"".join(page_links)}
                <a class="{next_cls}" href="{next_href}">&rsaquo;</a>
            </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_properties(ticket: dict):
    brand = html.escape(ticket.get("account_name") or "—")
    requester = html.escape(ticket["requester_name"])
    assignee = html.escape(ticket["assignee"])
    ticket_type = html.escape(ticket_type_label(ticket.get("category", "")))
    priority = html.escape(priority_label(ticket.get("priority", "")))
    tags = ticket.get("tags", [])
    tags_html = "".join(
        f'<span class="zd-tag-chip-blue">{html.escape(tag)}</span>' for tag in tags
    ) or '<span style="color:#87929d;">—</span>'

    arr_fmt = ticket.get("account_arr_formatted", "—")
    arr_field_html = ""
    if ticket.get("account_arr", 0) > 0 and arr_fmt != "—":
        arr_pill = f'<span class="zd-tag-chip">{html.escape(arr_fmt)} ARR</span>'
        arr_field_html = (
            '<div class="zd-prop">'
            '<div class="zd-prop-label">ARR</div>'
            f'<div class="zd-prop-tags">{arr_pill}</div>'
            "</div>"
        )

    region = ticket.get("account_region", "")
    region_field_html = ""
    if region:
        region_pill = f'<span class="zd-tag-chip">{html.escape(region)}</span>'
        region_field_html = (
            '<div class="zd-prop">'
            '<div class="zd-prop-label">region</div>'
            f'<div class="zd-prop-tags">{region_pill}</div>'
            "</div>"
        )

    st.markdown(
        f"""
        <div class="zd-props">
            <div class="zd-prop">
                <div class="zd-prop-label">Brand</div>
                <div class="zd-prop-select">
                    {brand}
                    <span class="zd-prop-chev">&#9662;</span>
                </div>
            </div>
            <div class="zd-prop">
                <div class="zd-prop-label">Requester</div>
                <div class="zd-prop-select">
                    {avatar_html(ticket["requester_name"], "sm")}
                    {requester}
                    <span class="zd-prop-chev">&#9662;</span>
                </div>
            </div>
            <div class="zd-prop">
                <div class="zd-prop-label">
                    Assignee
                    <span class="zd-prop-link">take it</span>
                </div>
                <div class="zd-prop-select">
                    {avatar_html(ticket["assignee"], "sm")}
                    {assignee}
                    <span class="zd-prop-chev">&#9662;</span>
                </div>
            </div>
            <div class="zd-prop">
                <div class="zd-prop-label">Tags</div>
                <div class="zd-prop-tags">{tags_html}</div>
            </div>
            {arr_field_html}{region_field_html}
            <div class="zd-prop">
                <div class="zd-prop-label">Type</div>
                <div class="zd-prop-select">
                    {ticket_type}
                    <span class="zd-prop-chev">&#9662;</span>
                </div>
            </div>
            <div class="zd-prop">
                <div class="zd-prop-label">Priority</div>
                <div class="zd-prop-select">
                    {priority}
                    <span class="zd-prop-chev">&#9662;</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_conversation(ticket: dict):
    requester = html.escape(ticket["requester_name"])
    via = html.escape(channel_via_label(ticket["channel"]))
    thread_html = render_conversation_thread_html(get_ticket_messages(ticket))

    st.markdown(
        f"""
        <div class="zd-conv-panel">
            <div class="zd-conv-header">
                <h2 class="zd-conv-title">Conversation with {requester}</h2>
                <div class="zd-conv-via">{via}</div>
            </div>
            {thread_html}
            <div class="zd-composer">
                <div class="zd-composer-tabs">
                    <span class="zd-composer-tab active">Messaging</span>
                    <span class="zd-composer-tab">Internal note</span>
                </div>
                <div class="zd-composer-to">To: {requester}</div>
                <div class="zd-composer-input">Type your reply…</div>
                <div class="zd-composer-toolbar">
                    <span>B</span><span>I</span><span>&#128206;</span><span>&#128247;</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_interaction_history(ticket: dict):
    subject = html.escape(truncate(ticket["subject"], 36))
    status_upper = ticket["status"].upper()
    date_str = html.escape(format_date(ticket["created_at"]))

    history_items = []
    past = get_interaction_history(ticket["id"], ticket.get("account_id"))
    for item in past:
        subj = html.escape(truncate(item["subject"], 36))
        d = html.escape(format_date(item["created_at"]))
        st_upper = item["status"].upper()
        href = f"?ticket={html.escape(item['id'], quote=True)}&mode=detail"
        history_items.append(
            f'<a class="zd-history-item" href="{href}" style="text-decoration:none;color:inherit;">'
            f'{status_icon_html(item["status"])}'
            f'<div><div class="zd-history-subj">{subj}</div>'
            f'<div class="zd-history-meta">{d} &middot; {st_upper}</div></div></a>'
        )

    st.markdown(
        f"""
        <div class="zd-props-history">
            <div class="zd-history-header">
                <span>Interaction history</span>
                <span class="zd-history-icons"><span>&#8942;</span><span>&#8635;</span></span>
            </div>
            <div class="zd-history-item active">
                {status_icon_html(ticket["status"])}
                <div>
                    <div class="zd-history-subj">{subject}</div>
                    <div class="zd-history-meta">{date_str} &middot; {status_upper}</div>
                </div>
            </div>
            {"".join(history_items)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_customer_context(ticket: dict):
    requester = html.escape(ticket["requester_name"])
    email = html.escape(ticket.get("requester_email") or "—")
    phone = html.escape(synthetic_phone(ticket["id"]))
    local_time = html.escape(format_local_time(ticket["created_at"]))
    note = html.escape(customer_note(ticket))

    st.markdown(
        f"""
        <div class="zd-context">
            <div class="zd-context-profile">
                <div class="zd-context-profile-top">
                    {avatar_html(ticket["requester_name"], "lg")}
                    <div class="zd-context-name">{requester}</div>
                </div>
                <div class="zd-context-row"><span class="lbl">Email</span> <a href="mailto:{email}">{email}</a></div>
                <div class="zd-context-row"><span class="lbl">Phone</span> {phone}</div>
                <div class="zd-context-row"><span class="lbl">Local time</span> {local_time}</div>
                <div class="zd-context-row"><span class="lbl">Language</span> English (United States)</div>
                <div class="zd-context-row"><span class="lbl">Notes</span></div>
                <div class="zd-context-notes">{note}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_analysis_from_api(ticket_id: str) -> dict:
    """Use FastAPI when available, otherwise run the analysis locally."""
    try:
        payload = json.dumps({"ticket_id": ticket_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{API_BASE}/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": f"API {exc.code}: {detail[:200]}"}
    except (urllib.error.URLError, TimeoutError, OSError) as api_exc:
        try:
            similar, trend, impact = run_analysis(ticket_id)
            engineering_draft = None
            engineering_draft_text = None
            if trend["is_potential_trend"]:
                engineering_draft = generate_engineering_ticket(
                    get_cache(), ticket_id, trend, similar, impact
                )
                engineering_draft_text = format_engineering_ticket_text(
                    engineering_draft
                )
            return {
                "ticket_id": ticket_id,
                "trigger": ticket_id,
                "similar_tickets": similar,
                "trend": trend,
                "impact": impact,
                "engineering_draft": engineering_draft,
                "engineering_draft_text": engineering_draft_text,
                "analysis_source": "local",
            }
        except Exception as local_exc:
            return {
                "error": (
                    f"API unavailable ({api_exc}); "
                    f"local analysis failed ({local_exc})"
                )
            }
    except Exception as exc:
        return {"error": str(exc)}


def render_api_results_html(data: dict) -> str:
    if "error" in data:
        return (
            f'<div class="trend-alert" style="border-left-color:#cc3340;background:#fde8e8;">'
            f"<strong>API unavailable</strong><br>"
            f"{html.escape(data['error'])}<br>"
            f'<span style="font-size:11px;color:#68737d;">'
            f"Start: uvicorn api.main:app --port 8000</span></div>"
        )

    trend = data.get("trend", {})
    impact = data.get("impact") or {}
    similar = data.get("similar_tickets") or []
    parts = []

    if trend.get("is_potential_trend"):
        parts.append(
            f'<div class="trend-alert"><strong>Potential trend detected</strong><br>'
            f"{trend.get('similar_count', 0)} earlier tickets at &ge; "
            f"{trend.get('threshold', 0.60):.0%} similarity in "
            f"{trend.get('window_days', 7)} days</div>"
        )
    else:
        parts.append(
            f'<div class="trend-ok"><strong>No trend detected</strong><br>'
            f"{trend.get('similar_count', 0)} earlier similar tickets "
            f"(requires &ge;{trend.get('min_count', 3)} at "
            f"&ge;{trend.get('threshold', 0.60):.0%} in "
            f"{trend.get('window_days', 7)} days)</div>"
        )

    if impact.get("unique_accounts", 0) > 0:
        parts.append(
            f'<div class="impact-card">'
            f'<div class="impact-title">Customer Impact (Salesforce)</div>'
            f'<div class="impact-row">&bull; {impact["unique_accounts"]} unique accounts</div>'
            f'<div class="impact-total">Total ARR at risk: '
            f'{html.escape(impact.get("arr_at_risk_formatted", "—"))}</div>'
            f"</div>"
        )

    parts.append('<div class="zd-section-label">Top 5 similar</div>')
    for i, item in enumerate(similar[:5], 1):
        ticket_id = html.escape(item.get("id", ""), quote=True)
        parts.append(
            f'<a class="similar-row" href="?ticket={ticket_id}&amp;mode=detail">'
            f'{i}. {html.escape(truncate(item.get("subject", ""), 48))}<br>'
            f'<span style="color:#68737d;font-size:11px;">'
            f'{html.escape(item.get("id", ""))} &middot; {item.get("similarity", 0):.0%} '
            f"&middot; {html.escape(item.get('category', ''))}</span></a>"
        )

    draft_text = data.get("engineering_draft_text")
    if draft_text:
        parts.append('<div class="zd-section-label">Engineering ticket draft</div>')
        parts.append(f'<div class="draft-box">{html.escape(draft_text)}</div>')
        draft = data.get("engineering_draft")
        if draft:
            quality = score_draft(draft)
            parts.append(
                '<div class="zd-section-label">Escalation Quality</div>'
                f'<div style="font-size:12px;line-height:1.4;color:#2f3941;">'
                f"{html.escape(format_quality_summary(quality))}</div>"
            )
        ticket_id = data.get("ticket_id") or st.session_state.get("selected_ticket_id")
        if ticket_id:
            jira_href = jira_view_in_jira_link(ticket_id)
            trend_href = trend_dashboard_url(ticket_id)
            if jira_href:
                parts.append(
                    f'<a class="jira-zd-create" href="{jira_href}">Open in Jira →</a>'
                )
            else:
                create_href = (
                    f"?ticket={html.escape(ticket_id, quote=True)}"
                    "&amp;mode=detail&amp;create_jira=1"
                )
                parts.append(
                    f'<a class="jira-zd-create" href="{create_href}">Create in Jira</a>'
                )
            parts.append(
                f'<a class="jira-zd-link" href="{trend_href}" '
                f'style="display:inline-block;margin-top:10px;margin-left:12px;">'
                "Review full trend →</a>"
            )

    return "".join(parts)


def ensure_detail_analysis(ticket_id: str) -> dict:
    api_key = f"api_results_{ticket_id}"
    rerun_requested = st.session_state.get("_analyze_requested") == ticket_id
    if rerun_requested:
        st.session_state.pop("_analyze_requested", None)

    if rerun_requested or api_key not in st.session_state:
        with st.spinner("Checking ticket for emerging trends…"):
            st.session_state[api_key] = fetch_analysis_from_api(ticket_id)
    return st.session_state[api_key]


def handle_jira_create_request() -> None:
    """Open the Jira Create issue draft screen; do not persist until Create."""
    ticket_id = st.session_state.pop("_create_jira_requested", None)
    create_open = _qp_value(st.query_params, "create") == "1"
    if not ticket_id and create_open and "_jira_create_draft" not in st.session_state:
        ticket_id = st.session_state.get("_jira_create_ticket") or st.session_state.get(
            "selected_ticket_id"
        )
    if not ticket_id:
        return
    if (
        create_open
        and st.session_state.get("_jira_create_draft")
        and st.session_state.get("_jira_create_ticket") == ticket_id
    ):
        return

    api_key = f"api_results_{ticket_id}"
    analysis = st.session_state.get(api_key) or fetch_analysis_from_api(ticket_id)
    st.session_state[api_key] = analysis
    confirmed_review = load_confirmed_review(ticket_id)
    draft = (
        confirmed_review.get("draft")
        if confirmed_review
        else analysis.get("engineering_draft")
    )
    if not draft:
        st.session_state["_jira_create_error"] = (
            "This ticket is below the trend threshold, so no Jira draft was created."
        )
        return

    st.session_state["_jira_create_ticket"] = ticket_id
    st.session_state["_jira_create_draft"] = draft
    st.session_state.page_mode = "jira"
    st.session_state.pop("jira_issue", None)
    set_query_params(
        mode="jira",
        create="1",
        ticket=ticket_id,
        issue=None,
        create_jira=None,
    )
    st.rerun()


def render_detail_apps_panel(ticket_id: str, analysis: dict):
    body_html = render_api_results_html(analysis)

    tid = html.escape(ticket_id)
    analyze_href = f"?ticket={tid}&amp;mode=detail&amp;analyze=1"
    st.markdown(
        f"""
        <div class="zd-apps-panel">
            <div class="zd-apps-divider"></div>
            <div class="zd-apps-header">Apps</div>
            <div class="zd-agent">
                <div class="zd-agent-card">
                    <div class="zd-agent-card-pad">
                        <div class="zd-agent-product">Support Operations</div>
                        <div class="zd-agent-title">Trend Detection</div>
                        <div class="zd-agent-sub">Similarity search and trend alerts</div>
                    </div>
                    <a class="zd-analyze-btn" data-ticket="{tid}" href="{analyze_href}">
                        Re-run analysis
                    </a>
                    <div class="zd-agent-card-pad zd-agent-card-pad-bottom">
                        {body_html}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_top_bar(ticket: dict, trend: dict):
    status_upper = ticket["status"].upper()
    badge_cls = status_badge_class(ticket["status"])
    requester = html.escape(ticket["requester_name"])
    tid = html.escape(ticket["id"])
    tid_num = tid.replace("T-", "")
    warning_html = ""
    if trend.get("is_potential_trend"):
        similar_count = int(trend.get("similar_count", 0))
        warning_html = (
            '<span class="zd-trend-warning" '
            f'title="{similar_count} similar tickets found">'
            f'&#9888; Potential trend ({similar_count})</span>'
        )

    top_bar_html = (
        '<div class="zd-detail-topbar">'
        '<div class="zd-detail-tabs">'
        f'<span class="zd-detail-status {badge_cls}">{status_upper}</span>'
        '<span class="zd-detail-tab">'
        '<span class="zd-detail-tab-icon">&#9993;</span>'
        f'Conversation with {requester} #{tid_num}'
        '</span>'
        f'<span class="zd-detail-ticket-label">Ticket #{tid}</span>'
        f'{warning_html}'
        '</div>'
        '<div class="zd-detail-toolbar">'
        '<span class="zd-detail-next">Next &#8250;</span>'
        '</div>'
        '</div>'
    )
    st.markdown(top_bar_html, unsafe_allow_html=True)


def render_ticket_detail(ticket: dict):
    requester = ticket["requester_name"]
    tid_num = ticket["id"].replace("T-", "")
    st.markdown('<div class="zd-detail-shell">', unsafe_allow_html=True)
    render_tab_bar(f"Conversation with {requester} #{tid_num}")
    st.markdown('<div class="zd-detail-tab-gap">&nbsp;</div>', unsafe_allow_html=True)

    if st.button("← Back to list", key="back_to_list"):
        back_to_ticket_list()
        st.rerun()

    analysis = ensure_detail_analysis(ticket["id"])
    render_detail_top_bar(ticket, analysis.get("trend", {}))

    st.markdown('<div class="zd-detail-inner">', unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([0.17, 0.43, 0.40])

    with col_left:
        render_detail_properties(ticket)
        render_detail_interaction_history(ticket)
    with col_center:
        render_detail_conversation(ticket)
    with col_right:
        render_detail_customer_context(ticket)
        render_detail_apps_panel(ticket["id"], analysis)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_agent_panel(ticket_id: str):
    st.markdown('<div class="zd-agent"><div class="zd-agent-card zd-agent-card-list">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="zd-agent-product">Support Operations</div>
        <div class="zd-agent-title">Trend Detection</div>
        <div class="zd-agent-sub">Similarity search and trend alerts</div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Analyze selected ticket", type="primary", use_container_width=True):
        with st.spinner("Analyzing…"):
            similar, trend, impact = run_analysis(ticket_id)
            st.session_state["results"] = {
                "similar": similar,
                "trend": trend,
                "impact": impact,
                "ticket_id": ticket_id,
            }

    if "results" not in st.session_state or st.session_state["results"]["ticket_id"] != ticket_id:
        st.markdown(
            '<div class="zd-hint">Select a ticket, then run analysis.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    results = st.session_state["results"]
    similar = results["similar"]
    trend = results["trend"]
    impact = results.get("impact")
    cache = get_cache()

    if trend["is_potential_trend"]:
        st.markdown(
            f"""
            <div class="trend-alert">
                <strong>Potential trend detected</strong><br>
                {trend['similar_count']} earlier tickets at &ge; {trend['threshold']:.0%}
                similarity in {trend.get('window_days', 7)} days
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="trend-ok">
                <strong>No trend detected</strong><br>
                {trend['similar_count']} earlier similar tickets
                (requires &ge;{trend.get('min_count', 3)} at &ge;{trend['threshold']:.0%}
                in {trend.get('window_days', 7)} days)
            </div>
            """,
            unsafe_allow_html=True,
        )

    if impact and impact["unique_accounts"] > 0:
        tier_lines = []
        for tier in ("enterprise", "pro", "free"):
            count = impact["by_tier"].get(tier, 0)
            if count:
                arr = format_arr(impact["arr_by_tier"].get(tier, 0))
                tier_lines.append(
                    f'<div class="impact-row">• {count} {tier} ({arr} ARR)</div>'
                )
        st.markdown(
            f"""
            <div class="impact-card">
                <div class="impact-title">Customer Impact (Salesforce)</div>
                <div class="impact-row">• {impact['unique_accounts']} unique accounts</div>
                {"".join(tier_lines)}
                <div class="impact-total">
                    Total ARR at risk: {impact['arr_at_risk_formatted']}
                </div>
                <div class="impact-source">Source: synthetic Salesforce account data</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="zd-section-label">Top 5 similar</div>', unsafe_allow_html=True)
    for i, item in enumerate(similar, 1):
        col_btn, col_info = st.columns([0.15, 0.85])
        with col_btn:
            st.markdown('<div class="zd-sim-btn">', unsafe_allow_html=True)
            if st.button(item["id"], key=f"sim_{item['id']}"):
                select_ticket(item["id"])
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_info:
            st.markdown(
                f"""
                <div class="similar-row">
                    {i}. {html.escape(truncate(item['subject'], 48))}<br>
                    <span style="color:#68737d;font-size:11px;">
                        {item['similarity']:.0%} &middot; {html.escape(item['category'])}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if trend["is_potential_trend"]:
        st.markdown(
            '<div class="zd-section-label">Engineering ticket draft</div>',
            unsafe_allow_html=True,
        )
        draft = generate_engineering_ticket(cache, ticket_id, trend, similar, impact)
        draft_text = format_engineering_ticket_text(draft)
        st.markdown(
            f'<div class="draft-box">{html.escape(draft_text)}</div>',
            unsafe_allow_html=True,
        )
        jira_href = jira_view_in_jira_link(ticket_id)
        if jira_href:
            st.markdown(
                f'<a class="jira-zd-link" href="{jira_href}">Open in Jira →</a>',
                unsafe_allow_html=True,
            )
        copy_button(draft_text, f"copy-{ticket_id}")
        with st.expander("Structured fields"):
            st.json(draft)

    st.markdown("</div></div>", unsafe_allow_html=True)


def main():
    scenarios = load_demo_scenarios()
    init_session_state(scenarios)
    sync_query_params()
    handle_jira_create_request()

    create_error = st.session_state.pop("_jira_create_error", None)
    if create_error:
        st.error(create_error)

    category_counts = get_category_counts()
    total_all = get_total_ticket_count()
    unsolved_count = get_unsolved_count()
    unassigned_count = get_unassigned_count()
    open_count = get_open_count()
    ticket_id = st.session_state.selected_ticket_id
    ticket = get_ticket_details(ticket_id)
    page_mode = st.session_state.page_mode
    is_detail = page_mode == "detail" and ticket is not None
    is_jira = page_mode == "jira"
    is_trend = page_mode == "trend"
    jira_issue = st.session_state.get("jira_issue")
    jira_filter = st.session_state.get("jira_filter", "all")
    jira_search = st.session_state.get("jira_search", "")
    jira_page = st.session_state.get("jira_page", 0)
    jira_nav = st.session_state.get("jira_nav", "backlog")

    if is_jira:
        create_open = _qp_value(st.query_params, "create") == "1"
        create_draft_ready = st.session_state.get("_jira_create_draft") is not None
        if create_open and create_draft_ready:
            body_class = "jira-create-mode"
        elif jira_issue and not create_open:
            body_class = "jira-detail-mode"
        else:
            body_class = "jira-mode"
    elif is_trend:
        body_class = "trend-mode"
    else:
        body_class = "zd-detail-mode" if is_detail else "zd-list-mode"
    components.html(
        f"""
        <script>
        (function () {{
          const parentDoc = window.parent.document;
          parentDoc.body.className = "{body_class}";
        }})();
        </script>
        """,
        height=0,
    )

    if is_jira:
        install_query_param_navigation()
        create_draft = st.session_state.get("_jira_create_draft")
        create_ticket = st.session_state.get("_jira_create_ticket")
        show_create = (
            _qp_value(st.query_params, "create") == "1" and create_draft is not None
        )
        render_jira_view(
            issue_key=None if show_create else jira_issue,
            status_filter=jira_filter,
            search=jira_search,
            page=jira_page,
            nav=jira_nav,
            create_draft=create_draft if show_create else None,
            create_ticket_id=create_ticket if show_create else None,
        )
        return

    if is_trend:
        install_query_param_navigation()
        render_trend_dashboard(ticket_id=ticket_id)
        return

    render_global_header()
    install_query_param_navigation()

    page = st.session_state.list_page
    tickets, total_filtered = list_tickets(
        category=st.session_state.category_filter,
        search=st.session_state.search_query,
        page=page,
    )

    if not is_detail and tickets:
        trend_signals = get_trend_signals(tuple(t["id"] for t in tickets))
        for ticket_row in tickets:
            ticket_row["trend_signal"] = trend_signals.get(ticket_row["id"], {})

    if is_detail:
        col_nav, col_rest = st.columns([0.04, 0.96])
        with col_nav:
            render_icon_nav()
        with col_rest:
            render_ticket_detail(ticket)
    else:
        col_nav, col_views, col_main = st.columns([0.04, 0.12, 0.84])

        with col_nav:
            render_icon_nav()

        with col_views:
            render_views_sidebar(
                category_counts,
                total_all,
                unsolved_count,
                unassigned_count,
                open_count,
                scenarios,
            )

        with col_main:
            st.markdown('<div class="zd-list-shell">', unsafe_allow_html=True)
            render_tab_bar(current_view_label(st.session_state.category_filter))
            render_view_header(total_filtered)
            render_ticket_table(tickets, total_filtered, page)
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
