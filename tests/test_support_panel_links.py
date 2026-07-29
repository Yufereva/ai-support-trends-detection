import app
from app import render_api_results_html


def test_similar_ticket_rows_link_to_zendesk_details():
    markup = render_api_results_html(
        {
            "trend": {"is_potential_trend": False},
            "similar_tickets": [
                {
                    "id": "T-20163",
                    "subject": "Workspace role persists after SCIM update",
                    "similarity": 0.97,
                    "category": "identity",
                },
                {
                    "id": "T-20173",
                    "subject": "Role persists after configuration change",
                    "similarity": 0.95,
                    "category": "identity",
                },
            ],
        }
    )

    assert markup.count('class="similar-row"') == 2
    assert '?ticket=T-20163&amp;mode=detail' in markup
    assert '?ticket=T-20173&amp;mode=detail' in markup


def test_existing_jira_issue_uses_open_label(monkeypatch):
    monkeypatch.setattr(
        app,
        "jira_view_in_jira_link",
        lambda _: "?mode=jira&amp;issue=ENG-151",
    )

    markup = render_api_results_html(
        {
            "ticket_id": "T-20168",
            "trend": {"is_potential_trend": True},
            "similar_tickets": [],
            "engineering_draft_text": "Reviewed engineering draft",
        }
    )

    assert "Open in Jira" in markup
    assert "View in Jira" not in markup
    assert "?mode=jira&amp;issue=ENG-151" in markup


def test_missing_jira_issue_uses_create_label(monkeypatch):
    monkeypatch.setattr(app, "jira_view_in_jira_link", lambda _: None)

    markup = render_api_results_html(
        {
            "ticket_id": "T-20168",
            "trend": {"is_potential_trend": True},
            "similar_tickets": [],
            "engineering_draft_text": "Reviewed engineering draft",
        }
    )

    assert "Create in Jira" in markup
    assert "Open in Jira" not in markup
