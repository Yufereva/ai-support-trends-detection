"""Bridge wiring for Escalation Quality inside Trend Detection."""

from unittest.mock import MagicMock

import pytest

import jira_view
from escalation_quality_bridge import format_quality_summary, quality_panel_html, score_draft


def _trend_shaped_draft():
    draft = {
        "title": "[Trend] Recurring Api issues (12 similar tickets)",
        "priority": "high",
        "category": "api",
        "trigger_ticket_id": "T-20168",
        "similar_count": 12,
        "similar_ticket_ids": ["T-20160", "T-20161", "T-20162", "T-20163"],
        "customer_impact": {
            "total_tickets": 13,
            "unique_accounts": 9,
            "by_tier": {"enterprise": 4},
            "arr_at_risk_formatted": "$484K",
        },
        "summary": (
            "Support trend detected: 12 tickets with similarity >= 60% to ticket T-20168.\n\n"
            "Category: api\nTrigger ticket: Webhook delivery retries exhaust and drop events.\n\n"
            "Customer impact:\n- 13 tickets, 9 unique accounts, 4 enterprise\n"
            "- Est. ARR at risk: $484K (Salesforce)\n\n"
            "Recommend engineering review for potential systemic api issue."
        ),
    }
    return draft


def test_bridge_scores_live_trend_shaped_draft():
    report = score_draft(_trend_shaped_draft())
    assert report["verdict"] == "needs_work"
    assert "Escalation quality: needs_work" in format_quality_summary(report)
    panel = quality_panel_html(report)
    assert "Soft gate" in panel
    assert panel.count(">Pass<") + panel.count(">Gap<") == 8


def test_jira_create_modal_renders_quality_panel_inside_dialog(monkeypatch):
    """The panel must live in the dialog markdown block, not between dialog and form."""

    class _StopAtForm(Exception):
        pass

    bodies: list[str] = []

    def _form(*_args, **_kwargs):
        raise _StopAtForm

    monkeypatch.setattr(jira_view.st, "markdown", lambda body, **_kw: bodies.append(body))
    monkeypatch.setattr(jira_view.st, "form", _form)
    monkeypatch.setattr(jira_view.st, "query_params", {})
    monkeypatch.setattr(
        jira_view.st,
        "session_state",
        MagicMock(**{"get.return_value": None}),
    )

    with pytest.raises(_StopAtForm):
        jira_view.render_jira_create_form("T-20168", _trend_shaped_draft())

    assert len(bodies) == 1
    dialog = bodies[0]
    assert "jira-create-dialog" in dialog
    assert dialog.index("Project") < dialog.index("Escalation Quality")
    assert "Soft gate" in dialog
    assert "Clear title" in dialog
    assert "Expected vs actual" in dialog
    assert dialog.count(">Pass<") + dialog.count(">Gap<") == 8


def _plain_description():
    """Description free of expected/actual/repro wording — enrichment must carry it."""
    return (
        "Support trend detected: 12 tickets with similarity >= 60% to ticket T-20168.\n\n"
        "Customer impact:\n- 13 tickets, 9 unique accounts, 4 enterprise\n"
        "- Est. ARR at risk: $484K (Salesforce)\n\n"
        "Recommend engineering review for potential systemic api issue."
    )


ENRICHMENT_INPUT = {
    "Expected behavior": "Webhook events are delivered after retry backoff.",
    "Actual behavior": "Events are dropped once retries are exhausted.",
    "Reproduction steps": "1. Send a webhook burst. 2. Force 500s. 3. Watch queue drain.",
    "Environment / version": "Staging us-west-2, build 1.2.3.",
}


def _form_stubs(monkeypatch, session, *, text_areas):
    class _FormCtx:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def _columns(spec, *_a, **_k):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MagicMock() for _ in range(n)]

    monkeypatch.setattr(jira_view.st, "markdown", lambda *_a, **_k: None)
    monkeypatch.setattr(jira_view.st, "form", lambda *_a, **_k: _FormCtx())
    monkeypatch.setattr(jira_view.st, "columns", _columns)
    monkeypatch.setattr(
        jira_view.st,
        "selectbox",
        lambda label, options, **kw: options[kw.get("index", 0)],
    )
    monkeypatch.setattr(
        jira_view.st,
        "text_input",
        lambda label, **kw: {
            "Summary *": "[Trend] Recurring Api issues (12 similar tickets)",
            "Assignee": "Unassigned",
            "Labels": "trend-warning, api",
            "Category": "api",
            "ARR at risk": "$484K",
        }.get(label, kw.get("value", "")),
    )
    monkeypatch.setattr(
        jira_view.st,
        "text_area",
        lambda label, **kw: text_areas.get(label, kw.get("value", "")),
    )
    monkeypatch.setattr(jira_view.st, "caption", lambda *_a, **_k: None)
    monkeypatch.setattr(jira_view.st, "checkbox", lambda *_a, **_k: False)
    monkeypatch.setattr(jira_view.st, "query_params", {})
    monkeypatch.setattr(jira_view.st, "session_state", session)


def test_enrichment_fields_from_form_move_verdict_to_ready(monkeypatch, tmp_path):
    """Expected/Actual/Repro/Environment fields alone must satisfy the checklist."""
    session: dict = {}
    monkeypatch.setattr(
        jira_view, "CREATE_ENRICHMENT_PATH", tmp_path / "jira_create_enrichment.json"
    )
    _form_stubs(
        monkeypatch,
        session,
        text_areas={"Description": _plain_description(), **ENRICHMENT_INPUT},
    )
    monkeypatch.setattr(
        jira_view.st,
        "form_submit_button",
        lambda label, **_kw: label == "Re-check escalation quality",
    )
    monkeypatch.setattr(jira_view.st, "rerun", lambda: None)

    assert score_draft({**_trend_shaped_draft(), "summary": _plain_description()})[
        "verdict"
    ] == "needs_work"

    jira_view.render_jira_create_form("T-20168", _trend_shaped_draft())

    report = session["_jira_create_quality_T-20168"]
    assert report["verdict"] == "ready"
    assert report["gaps"] == []
    draft = session["_jira_create_draft"]
    assert draft["expected_behavior"] == ENRICHMENT_INPUT["Expected behavior"]
    assert draft["environment"] == ENRICHMENT_INPUT["Environment / version"]


def test_enrichment_survives_refresh_and_reaches_created_issue(monkeypatch, tmp_path):
    """Values persist for a reopened form and land in the stored issue description."""
    monkeypatch.setattr(
        jira_view, "CREATE_ENRICHMENT_PATH", tmp_path / "jira_create_enrichment.json"
    )
    monkeypatch.setattr(jira_view, "JIRA_SEED_PATH", tmp_path / "seed.json")
    monkeypatch.setattr(jira_view, "JIRA_ISSUES_PATH", tmp_path / "issues.json")
    (tmp_path / "seed.json").write_text('{"issues": []}', encoding="utf-8")

    _form_stubs(
        monkeypatch,
        {},
        text_areas={"Description": _plain_description(), **ENRICHMENT_INPUT},
    )
    monkeypatch.setattr(
        jira_view.st,
        "form_submit_button",
        lambda label, **_kw: label == "Re-check escalation quality",
    )
    monkeypatch.setattr(jira_view.st, "rerun", lambda: None)
    jira_view.render_jira_create_form("T-20168", _trend_shaped_draft())

    # A refresh drops session state; the reopened form re-scores from the store.
    reopened = jira_view.load_create_enrichment("T-20168")
    assert reopened["reproduction_steps"] == ENRICHMENT_INPUT["Reproduction steps"]
    assert score_draft({**_trend_shaped_draft(), **reopened})["verdict"] == "ready"

    created: list[dict] = []
    session: dict = {}
    _form_stubs(
        monkeypatch,
        session,
        text_areas={"Description": _plain_description(), **ENRICHMENT_INPUT},
    )
    monkeypatch.setattr(
        jira_view.st, "form_submit_button", lambda label, **_kw: label == "Create"
    )
    monkeypatch.setattr(jira_view.st, "rerun", lambda: None)
    monkeypatch.setattr(jira_view, "_finish_jira_create", lambda issue: created.append(issue))

    jira_view.render_jira_create_form("T-20168", _trend_shaped_draft())

    issue = created[0]
    assert issue["expected_behavior"] == ENRICHMENT_INPUT["Expected behavior"]
    for label, value in ENRICHMENT_INPUT.items():
        assert f"{label}:\n{value}" in issue["description"]


def test_jira_create_recheck_scores_edited_form_without_creating(monkeypatch, tmp_path):
    """Re-check merges current form edits, re-scores, and does not create an issue."""
    monkeypatch.setattr(
        jira_view, "CREATE_ENRICHMENT_PATH", tmp_path / "jira_create_enrichment.json"
    )

    class _FormCtx:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    session: dict = {}
    submit_calls: list[str] = []
    create_calls: list = []
    rerun_calls: list = []

    def _submit(label, **kwargs):
        submit_calls.append(label)
        return label == "Re-check escalation quality"

    monkeypatch.setattr(jira_view.st, "markdown", lambda *_a, **_k: None)
    monkeypatch.setattr(jira_view.st, "form", lambda *_a, **_k: _FormCtx())
    def _columns(spec, *_a, **_k):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MagicMock() for _ in range(n)]

    monkeypatch.setattr(jira_view.st, "columns", _columns)
    monkeypatch.setattr(
        jira_view.st,
        "selectbox",
        lambda label, options, **kw: options[kw.get("index", 0)],
    )
    monkeypatch.setattr(
        jira_view.st,
        "text_input",
        lambda label, **kw: {
            "Summary *": "[Trend] Recurring Api issues (12 similar tickets)",
            "Assignee": "Unassigned",
            "Labels": "trend-warning, api",
            "Category": "api",
            "ARR at risk": "$484K",
        }.get(label, kw.get("value", "")),
    )
    monkeypatch.setattr(
        jira_view.st,
        "text_area",
        lambda *_a, **_k: (
            "Support trend detected: 12 tickets with similarity >= 60% to ticket T-20168.\n\n"
            "Expected behavior: events are delivered after retries.\n"
            "Actual behavior: events are dropped after retry exhaustion.\n"
            "Reproduction steps: send webhook burst in staging region us-west-2.\n"
            "Environment: staging, build 1.2.3.\n\n"
            "Customer impact:\n- 13 tickets, 9 unique accounts, 4 enterprise\n"
            "- Est. ARR at risk: $484K (Salesforce)\n\n"
            "Recommend engineering review for potential systemic api issue."
        ),
    )
    monkeypatch.setattr(jira_view.st, "caption", lambda *_a, **_k: None)
    monkeypatch.setattr(jira_view.st, "checkbox", lambda *_a, **_k: False)
    monkeypatch.setattr(jira_view.st, "form_submit_button", _submit)
    monkeypatch.setattr(jira_view.st, "query_params", {})
    monkeypatch.setattr(jira_view.st, "session_state", session)
    monkeypatch.setattr(jira_view.st, "rerun", lambda: rerun_calls.append(True))
    monkeypatch.setattr(
        jira_view,
        "create_jira_issue",
        lambda *a, **k: create_calls.append((a, k)) or {"key": "SUP-999"},
    )

    jira_view.render_jira_create_form("T-20168", _trend_shaped_draft())

    assert create_calls == []
    assert rerun_calls == [True]
    assert "Re-check escalation quality" in submit_calls
    quality_key = "_jira_create_quality_T-20168"
    assert quality_key in session
    assert session[quality_key]["verdict"] == "ready"
    assert session[quality_key]["gaps"] == []
