"""Streamlit review interface for AI Support Trends Detection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from support_trend_detection.config import DEFAULT_DATA_PATH  # noqa: E402
from support_trend_detection.pipeline import run_pipeline  # noqa: E402
from support_trend_detection.reporting import trend_to_markdown  # noqa: E402


st.set_page_config(
    page_title="AI Support Trends Detection",
    layout="wide",
)


def load_input_data(uploaded_file) -> pd.DataFrame | str:
    if uploaded_file is None:
        return str(DEFAULT_DATA_PATH)
    return pd.read_csv(uploaded_file)


def render_metric(label: str, value: str | int, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def main() -> None:
    st.title("AI Support Trends Detection")
    st.caption(
        "Portfolio MVP for identifying emerging support ticket patterns and "
        "preparing evidence-backed Product and Engineering review."
    )

    st.info(
        "All sample data in this repository is synthetic. No customer or former employer "
        "data is included."
    )

    with st.sidebar:
        st.header("Analysis setup")
        uploaded_file = st.file_uploader("Optional CSV upload", type=["csv"])
        current_days = st.slider("Current period (days)", 7, 30, 14)
        previous_days = st.slider("Previous period (days)", 7, 30, 14)
        max_trends = st.slider("Max trends", 3, 12, 8)
        run_clicked = st.button("Run trend analysis", type="primary")

    data = load_input_data(uploaded_file)
    should_run = run_clicked or "analysis_results" not in st.session_state

    if should_run:
        try:
            tickets, trends = run_pipeline(
                data,
                current_days=current_days,
                previous_days=previous_days,
                max_trends=max_trends,
            )
            st.session_state["analysis_results"] = (tickets, trends)
        except Exception as exc:  # pragma: no cover - Streamlit display path
            st.error(f"Could not run analysis: {exc}")
            return

    tickets, trends = st.session_state["analysis_results"]

    st.subheader("Dataset overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Tickets", len(tickets))
    with c2:
        render_metric("Product areas", tickets["product_area"].nunique())
    with c3:
        render_metric("Enterprise tickets", int((tickets["customer_tier"] == "enterprise").sum()))
    with c4:
        render_metric("Detected trends", len(trends))

    st.subheader("Ranked detected trends")
    if not trends:
        st.warning("No review-worthy trends were detected in the selected period.")
        return

    trend_rows = [
        {
            "Trend": trend.title,
            "Classification": trend.classification,
            "Priority": trend.priority,
            "Current": trend.current_volume,
            "Previous": trend.previous_volume,
            "Growth": f"{round(trend.growth_rate * 100)}%",
            "Enterprise tickets": trend.enterprise_ticket_count,
            "Confidence": trend.confidence,
        }
        for trend in trends
    ]
    st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

    trend_labels = [f"{trend.priority} - {trend.title}" for trend in trends]
    selected_label = st.selectbox("Review trend", trend_labels)
    selected_trend = trends[trend_labels.index(selected_label)]

    left, right = st.columns([0.58, 0.42])
    with left:
        st.markdown(f"### {selected_trend.title}")
        st.write(selected_trend.summary)
        st.markdown("#### Evidence")
        st.write(
            f"{selected_trend.current_volume} current-period tickets vs "
            f"{selected_trend.previous_volume} prior-period tickets."
        )
        st.write(f"Growth: **{round(selected_trend.growth_rate * 100)}%**")
        st.write(f"Product areas: {', '.join(selected_trend.product_areas)}")
        st.write(f"Supporting tickets: {', '.join(selected_trend.supporting_ticket_ids)}")

    with right:
        st.markdown("#### Customer impact")
        st.write(selected_trend.customer_impact)
        st.markdown("#### Recommended next action")
        st.write(selected_trend.recommended_action)
        st.markdown("#### Confidence")
        st.write(f"**{selected_trend.confidence}** - {selected_trend.confidence_reason}")

    st.subheader("Download analysis")
    result_json = json.dumps([trend.to_dict() for trend in trends], indent=2)
    st.download_button(
        "Download trends JSON",
        data=result_json,
        file_name="support_trends.json",
        mime="application/json",
    )
    st.download_button(
        "Download selected trend report",
        data=trend_to_markdown(selected_trend),
        file_name="trend_report.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
