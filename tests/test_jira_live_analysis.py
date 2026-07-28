import json

import jira_view


def test_linked_jira_issue_replaces_stored_metrics_with_live_analysis(monkeypatch):
    stored_issue = {
        "key": "ENG-999",
        "summary": "Stale summary",
        "description": "Stale description with 47 tickets",
        "priority": "Low",
        "zendesk_ticket_count": 47,
        "arr_at_risk": "$999K",
        "trigger_ticket_id": "T-0004",
    }
    live_analysis = {
        "trend": {"similar_count": 13},
        "impact": {"total_tickets": 14, "arr_at_risk_formatted": "$214K"},
        "draft": {
            "title": "[Trend] Recurring API issues (13 similar tickets)",
            "summary": "Live evidence from similarity analysis.",
            "priority": "medium",
        },
        "linked_support_tickets": [
            {"id": "T-0004", "subject": "Trigger", "relationship": "Trigger"},
            {"id": "T-0003", "subject": "Earlier match", "relationship": "Similar"},
        ],
    }
    monkeypatch.setattr(jira_view, "_live_trend_analysis", lambda _: live_analysis)

    issue = jira_view.hydrate_linked_issue(stored_issue)

    assert issue["similar_ticket_count"] == 13
    assert issue["zendesk_ticket_count"] == 14
    assert issue["arr_at_risk"] == "$214K"
    assert issue["summary"] == "[Trend] Recurring API issues (13 similar tickets)"
    assert issue["description"] == "Live evidence from similarity analysis."
    assert issue["analysis_source"] == "live"
    assert len(issue["linked_support_tickets"]) == 2


def test_linked_support_evidence_lists_every_zendesk_ticket():
    issue = {
        "linked_support_tickets": [
            {"id": "T-0004", "subject": "Trigger ticket", "relationship": "Trigger"},
            {"id": "T-0003", "subject": "First match", "relationship": "Similar"},
            {"id": "T-0002", "subject": "Second match", "relationship": "Similar"},
        ]
    }

    markup = jira_view._linked_support_evidence_html(issue)

    assert markup.count('class="jira-evidence-ticket"') == 3
    assert "?ticket=T-0004&amp;mode=detail" in markup
    assert "?ticket=T-0003&amp;mode=detail" in markup
    assert "?ticket=T-0002&amp;mode=detail" in markup
    assert markup.count(">Trigger<") == 1
    assert markup.count(">Similar<") == 2


def test_unlinked_jira_issue_is_not_changed(monkeypatch):
    issue = {"key": "ENG-100", "zendesk_ticket_count": 8}
    monkeypatch.setattr(
        jira_view,
        "_live_trend_analysis",
        lambda _: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    assert jira_view.hydrate_linked_issue(issue) is issue


def test_stale_linked_jira_issue_keeps_stored_data(monkeypatch):
    issue = {
        "key": "ENG-135",
        "summary": "Stored historical issue",
        "zendesk_ticket_count": 12,
        "trigger_ticket_id": "T-8454",
    }
    monkeypatch.setattr(
        jira_view,
        "_live_trend_analysis",
        lambda _: (_ for _ in ()).throw(ValueError("ticket not found in cache")),
    )

    assert jira_view.hydrate_linked_issue(issue) is issue


def test_create_jira_issue_writes_runtime_once(monkeypatch):
    seed_path = jira_view.ROOT / "data" / "runtime" / "test-jira-seed.json"
    runtime_path = jira_view.ROOT / "data" / "runtime" / "test-jira-created.json"
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    seed_path.write_text(
        json.dumps({"issues": [{"key": "ENG-150", "summary": "Existing issue"}]}),
        encoding="utf-8",
    )
    runtime_path.unlink(missing_ok=True)
    monkeypatch.setattr(jira_view, "JIRA_SEED_PATH", seed_path)
    monkeypatch.setattr(jira_view, "JIRA_ISSUES_PATH", runtime_path)

    draft = {
        "title": "[Trend] Recurring Identity issues",
        "summary": "Eight related access-removal tickets need review.",
        "priority": "high",
        "category": "identity",
        "similar_count": 8,
        "customer_impact": {
            "total_tickets": 9,
            "arr_at_risk_formatted": "$484K",
        },
    }

    try:
        created = jira_view.create_jira_issue("T-20168", draft)
        repeated = jira_view.create_jira_issue("T-20168", draft)
        revised_draft = {
            **draft,
            "title": "[Trend] Reviewed Identity cluster",
            "similar_count": 6,
            "customer_impact": {
                "total_tickets": 7,
                "arr_at_risk_formatted": "$374K",
            },
        }
        updated = jira_view.create_jira_issue("T-20168", revised_draft)
        stored = json.loads(runtime_path.read_text(encoding="utf-8"))["issues"]

        assert created["key"] == "ENG-151"
        assert created["trigger_ticket_id"] == "T-20168"
        assert created["arr_at_risk"] == "$484K"
        assert repeated["key"] == created["key"]
        assert updated["key"] == created["key"]
        assert updated["summary"] == "[Trend] Reviewed Identity cluster"
        assert updated["zendesk_ticket_count"] == 7
        assert updated["arr_at_risk"] == "$374K"
        assert len(stored) == 2
    finally:
        seed_path.unlink(missing_ok=True)
        runtime_path.unlink(missing_ok=True)
