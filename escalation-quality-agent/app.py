"""Escalation Quality Agent — Streamlit demo dashboard."""

from __future__ import annotations

import html
import json

import streamlit as st

from escalation_quality import format_quality_summary, load_drafts, score_all_drafts, score_draft

st.set_page_config(
    page_title="Escalation Quality Agent",
    page_icon="✅",
    layout="wide",
)

VERDICT_STYLE = {
    "ready": ("#2f9e44", "Ready for Engineering"),
    "needs_work": ("#f59f00", "Needs work"),
    "poor": ("#e35b5b", "Poor — too thin"),
}

st.markdown(
    """
    <style>
    .eq-hero { font-family: Georgia, "Times New Roman", serif; }
    .eq-hero h1 { font-size: 2rem; margin-bottom: 0.25rem; }
    .eq-hero p { color: #4b5563; font-size: 1.05rem; max-width: 52rem; }
    .eq-card {
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 16px 18px;
      margin-bottom: 14px;
      background: #fff;
    }
    .eq-badge {
      display: inline-block;
      color: #fff;
      font-size: 12px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 999px;
      margin-right: 8px;
    }
    .eq-meta { color: #6b7280; font-size: 13px; margin-top: 6px; }
    .eq-check-pass { color: #2f9e44; }
    .eq-check-fail { color: #c92a2a; }
    .eq-draft {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="eq-hero">
      <h1>Escalation Quality Agent</h1>
      <p>
        Scores a support→engineering escalation draft against an explicit checklist
        before Create in Jira. Recommendations only — a reviewer decides whether to proceed.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

reports = score_all_drafts()
counts = {
    "ready": sum(1 for r in reports if r["verdict"] == "ready"),
    "needs_work": sum(1 for r in reports if r["verdict"] == "needs_work"),
    "poor": sum(1 for r in reports if r["verdict"] == "poor"),
}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Drafts scored", len(reports))
c2.metric("Ready", counts["ready"])
c3.metric("Needs work", counts["needs_work"])
c4.metric("Poor", counts["poor"])

filter_choice = st.selectbox(
    "Filter by verdict",
    ["All", "ready", "needs_work", "poor"],
    format_func=lambda v: {
        "All": "All drafts",
        "ready": "Ready",
        "needs_work": "Needs work",
        "poor": "Poor",
    }.get(v, v),
)

drafts_by_id = {d["id"]: d for d in load_drafts()}
visible = [
    r for r in reports if filter_choice == "All" or r["verdict"] == filter_choice
]

for report in visible:
    draft = drafts_by_id[report["draft_id"]]
    color, label = VERDICT_STYLE[report["verdict"]]
    st.markdown(
        f"""
        <div class="eq-card">
          <span class="eq-badge" style="background:{color};">{html.escape(label)}</span>
          <strong>{html.escape(draft.get("label") or report["title"] or report["draft_id"])}</strong>
          <div class="eq-meta">
            {html.escape(report["draft_id"])} · {report["score_pct"]}% ·
            {report["passed_count"]}/{report["check_count"]} checks
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f"Checklist — {report['draft_id']}", expanded=report["verdict"] != "ready"):
        st.caption(format_quality_summary(report))
        st.write(report["recommendation"])
        for check in report["checks"]:
            mark = "PASS" if check["passed"] else "GAP"
            css = "eq-check-pass" if check["passed"] else "eq-check-fail"
            req = " · required" if check["required_for_ready"] else ""
            st.markdown(
                f'<span class="{css}"><strong>{mark}</strong> — '
                f'{html.escape(check["label"])}{req}: '
                f'{html.escape(check["detail"])}</span>',
                unsafe_allow_html=True,
            )
        st.markdown("**Draft text**")
        st.markdown(
            f'<div class="eq-draft">{html.escape(draft.get("summary", ""))}</div>',
            unsafe_allow_html=True,
        )

st.divider()
st.subheader("Score a pasted Trend Detection draft shape")
st.caption(
    "Paste JSON matching ``generate_engineering_ticket`` output, or use the live "
    "panel inside Trend Detection before Create in Jira."
)
sample = drafts_by_id["EQ-LIVE-SHAPE-001"]
pasted = st.text_area(
    "Draft JSON",
    value=json.dumps(
        {k: v for k, v in sample.items() if k not in {"label", "expected_verdict"}},
        indent=2,
    ),
    height=260,
)
if st.button("Score pasted draft", type="primary"):
    try:
        payload = json.loads(pasted)
        live_report = score_draft(payload)
        color, label = VERDICT_STYLE[live_report["verdict"]]
        st.markdown(
            f'<span class="eq-badge" style="background:{color};">{html.escape(label)}</span> '
            f'{live_report["score_pct"]}% — {html.escape(live_report["recommendation"])}',
            unsafe_allow_html=True,
        )
        for check in live_report["checks"]:
            mark = "PASS" if check["passed"] else "GAP"
            st.write(f"{mark}: {check['label']} — {check['detail']}")
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
