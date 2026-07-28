"""Generate synthetic Jira engineering escalation issues for the Trend Detection demo."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "jira_issues.json"

ENGINEERS = [
    "Alex Chen",
    "Maria Santos",
    "James Wright",
    "Priya Sharma",
    "David Chen",
    "Unassigned",
    "Elena Volkov",
    "Marcus Webb",
    "Nina Patel",
    "Ryan O'Brien",
]

REPORTERS = [
    "Sarah Mitchell",
    "Jake Rivera",
    "Emily Nakamura",
    "Chris Donovan",
    "Aisha Khan",
    "Tom Berger",
    "Lisa Fontaine",
    "Kevin Brooks",
    "Rachel Stein",
    "Omar Hassan",
]

PRIORITIES = ["Urgent", "High", "Medium", "Low"]
STATUSES = ["Open", "In Progress", "Done", "To Do"]
TYPES = ["Bug", "Story", "Task"]

HERO_ISSUES = [
    {
        "key": "ENG-138",
        "type": "Bug",
        "priority": "Medium",
        "summary": "[Trend] Billing invoice discrepancies across accounts",
        "description": (
            "Trend Detection escalation linked to trigger ticket T-0001. "
            "Similarity evidence and customer impact are populated from live analysis at runtime."
        ),
        "status": "Open",
        "assignee": "Unassigned",
        "reporter": "Jake Rivera",
        "labels": ["trend-warning", "support-escalation", "billing"],
        "created": "2026-07-09",
        "trigger_ticket_id": "T-0001",
    },
    {
        "key": "ENG-135",
        "type": "Bug",
        "priority": "High",
        "summary": "[Trend] Push notifications not delivered to mobile clients",
        "description": (
            "Trend Detection escalation linked to trigger ticket T-8454. "
            "Similarity evidence and customer impact are populated from live analysis at runtime."
        ),
        "status": "Open",
        "assignee": "Maria Santos",
        "reporter": "Emily Nakamura",
        "labels": ["trend-warning", "support-escalation", "mobile", "notifications"],
        "created": "2026-07-10",
        "trigger_ticket_id": "T-8454",
    },
]

INDEPENDENT_ISSUES = [
    # API failures / rate limits / auth errors
    ("ENG-101", "Bug", "Urgent", "Production API returning 429 for valid enterprise keys",
     "Support escalation context: 8 enterprise accounts hit rate limits despite Pro tier quotas. "
     "Logs show shared Redis counter not resetting at window boundary.", "In Progress", "api", 12),
    ("ENG-102", "Bug", "High", "OAuth token refresh fails with invalid_grant after 24h",
     "Support escalation context: 14 tickets report users logged out daily. Refresh endpoint "
     "returns invalid_grant; access tokens expire but refresh tokens appear valid in DB.", "Open", "api", 14),
    ("ENG-103", "Bug", "High", "GraphQL API auth middleware rejects Bearer tokens with scopes",
     "Support escalation context: REST API works; GraphQL returns 403 for same token. "
     "Started after deploy v2.4.2.", "Open", "api", 6),
    ("ENG-104", "Task", "Medium", "Document API rate limit headers in developer portal",
     "Support escalation context: 19 tickets asking about X-RateLimit headers with no KB coverage.", "Done", "api", 19),
    ("ENG-105", "Bug", "Urgent", "API gateway returning 502 on /v2/users bulk endpoint",
     "Support escalation context: Bulk user sync failing for 5 integration partners since 06:00 UTC.", "In Progress", "api", 5),
    ("ENG-106", "Bug", "Medium", "Webhook signature validation failing for rotated secrets",
     "Support escalation context: Customers who rotated webhook secrets see 401 on delivery retries.", "Open", "api", 7),
    ("ENG-107", "Bug", "High", "Service account JWT expires immediately after issuance",
     "Support escalation context: Machine-to-machine auth broken in EU region only.", "In Progress", "api", 9),
    ("ENG-108", "Story", "Low", "Add retry-after header to rate limit responses",
     "Support escalation context: Integrators cannot parse backoff timing from 429 responses.", "To Do", "api", 4),
    # Mobile app crashes / push notifications
    ("ENG-109", "Bug", "Urgent", "iOS app crash on launch — SIGABRT in CoreData migration",
     "Support escalation context: 34 crash reports from App Store Connect after v3.2.1.", "In Progress", "mobile", 34),
    ("ENG-110", "Bug", "High", "Android background sync killed by OS battery optimizer",
     "Support escalation context: 11 enterprise users miss offline data sync on Pixel devices.", "Open", "mobile", 11),
    ("ENG-111", "Bug", "Medium", "In-app notification badge count stuck at 99+",
     "Support escalation context: Badge counter not clearing after read; affects iOS 17+.", "Open", "mobile", 8),
    ("ENG-112", "Bug", "High", "Deep links from push open blank WebView",
     "Support escalation context: Tapping notification opens app but target page is white screen.", "Open", "mobile", 15),
    # Billing/payment webhook failures
    ("ENG-113", "Bug", "Urgent", "Stripe webhook handler dropping invoice.paid events",
     "Support escalation context: 6 accounts show paid in Stripe but subscription still past_due.", "In Progress", "billing", 6),
    ("ENG-114", "Bug", "High", "PayPal IPN verification failing after cert rotation",
     "Support escalation context: PayPal renewals not updating; 9 tickets since cert change.", "Open", "billing", 9),
    ("ENG-115", "Bug", "High", "Usage metering webhook delayed 4+ hours",
     "Support escalation context: Overage charges applied incorrectly due to stale usage data.", "Open", "billing", 12),
    ("ENG-116", "Bug", "Medium", "Tax calculation webhook timeout on EU VAT rules",
     "Support escalation context: Checkout fails for DE/FR customers; Avalara callback times out.", "Open", "billing", 5),
    # Data export/import bugs
    ("ENG-117", "Bug", "High", "CSV export timeout on datasets over 10k rows",
     "Support escalation context: Export job queue not scaling; 42 tickets at peak.", "Done", "export", 42),
    ("ENG-118", "Bug", "Medium", "Import wizard fails silently on UTF-8 BOM files",
     "Support escalation context: Excel-exported CSVs with BOM cause empty import with no error.", "Open", "export", 7),
    ("ENG-119", "Bug", "High", "Bulk import duplicates records on retry",
     "Support escalation context: Idempotency key not honored; customers got 2x records.", "In Progress", "export", 4),
    ("ENG-120", "Bug", "Medium", "PDF export missing embedded fonts for CJK characters",
     "Support escalation context: Japanese customers receive garbled PDF reports.", "Open", "export", 6),
    # SSO / SAML login breaks
    ("ENG-121", "Bug", "Urgent", "SAML SSO login fails after IdP certificate rotation",
     "Support escalation context: 58 tickets, 24 accounts; 503 on /api/auth/login post-deploy.", "In Progress", "sso", 58),
    ("ENG-122", "Bug", "High", "Okta SCIM provisioning creates users in wrong org",
     "Support escalation context: Multi-tenant mapping broken; users land in default org.", "Open", "sso", 10),
    ("ENG-123", "Bug", "High", "Azure AD group sync not removing deactivated users",
     "Support escalation context: Offboarded employees retain access; 3 security escalations.", "Open", "sso", 3),
    ("ENG-124", "Story", "Medium", "Improve MFA reset self-service flow",
     "Support escalation context: 35 tickets about MFA device loss with no documented workaround.", "Open", "sso", 35),
    # Performance degradation after deploy
    ("ENG-125", "Bug", "Urgent", "Dashboard load time 8s+ after v2.4.1 deploy",
     "Support escalation context: 20 tickets report timeouts; p95 latency up 400%.", "In Progress", "performance", 20),
    ("ENG-126", "Bug", "High", "Search index stale for 30+ minutes post-deploy",
     "Support escalation context: New records invisible in global search after releases.", "Open", "performance", 8),
    ("ENG-127", "Bug", "Medium", "Report generation CPU spike causing pod restarts",
     "Support escalation context: Scheduled reports fail during peak hours.", "Open", "performance", 5),
    ("ENG-128", "Bug", "High", "Memory leak in websocket connection handler",
     "Support escalation context: Real-time updates stop after ~2h; requires pod restart.", "In Progress", "performance", 6),
    # Integration webhooks (Slack, Salesforce)
    ("ENG-129", "Bug", "High", "Slack outbound webhook returns 500 on thread replies",
     "Support escalation context: Slack integration broken for threaded messages since API change.", "Open", "integrations", 11),
    ("ENG-130", "Bug", "High", "Salesforce sync failing on custom object mappings",
     "Support escalation context: 7 enterprise accounts; Opportunity sync returns FIELD_INTEGRITY_EXCEPTION.", "In Progress", "integrations", 7),
    ("ENG-131", "Bug", "Medium", "Microsoft Teams card actions not registering clicks",
     "Support escalation context: Adaptive card action URLs missing tenant context.", "Open", "integrations", 4),
    ("ENG-132", "Bug", "High", "HubSpot webhook retry storm exhausting rate limit",
     "Support escalation context: Failed deliveries retry without backoff; blocks other integrations.", "Open", "integrations", 3),
    # Database timeout / 503 errors
    ("ENG-133", "Bug", "Urgent", "PostgreSQL connection pool exhausted under load",
     "Support escalation context: 503 errors on 40% of requests during business hours.", "In Progress", "database", 18),
    ("ENG-134", "Bug", "High", "Read replica lag causing stale dashboard data",
     "Support escalation context: Users see data from 15+ minutes ago; 9 tickets.", "Open", "database", 9),
    ("ENG-136", "Bug", "High", "Deadlock on concurrent user profile updates",
     "Support escalation context: 503 on PATCH /users/{id} when two admins edit same user.", "Open", "database", 5),
    ("ENG-137", "Bug", "Medium", "Migration job locking tables during business hours",
     "Support escalation context: Schema migration ran at 14:00 UTC; caused 12 min outage.", "Done", "database", 12),
    # Feature flags not applying
    ("ENG-139", "Bug", "High", "LaunchDarkly flag evaluation returns default for EU tenants",
     "Support escalation context: New checkout flow not visible to EU customers despite flag on.", "Open", "feature-flags", 8),
    ("ENG-140", "Bug", "Medium", "Feature flag cache not invalidating after toggle",
     "Support escalation context: Support enabled beta for customer; still sees old UI after 1h.", "Open", "feature-flags", 6),
    ("ENG-141", "Bug", "High", "Percentage rollout stuck at 0% for canary cohort",
     "Support escalation context: Canary release not receiving traffic; blocks staged rollout.", "In Progress", "feature-flags", 2),
    ("ENG-143", "Bug", "Low", "Admin UI shows stale flag state vs evaluation API",
     "Support escalation context: Dashboard and API disagree on flag status; confuses support.", "To Do", "feature-flags", 3),
    # Kubernetes/deploy issues
    ("ENG-144", "Bug", "Urgent", "Rolling deploy stuck — new pods failing readiness probe",
     "Support escalation context: Deploy v2.4.3 rolled back; readiness check hits wrong health endpoint.", "In Progress", "kubernetes", 1),
    ("ENG-145", "Bug", "High", "HPA not scaling API pods during traffic spike",
     "Support escalation context: Manual scale needed; autoscaling metrics not collected.", "Open", "kubernetes", 4),
    ("ENG-146", "Bug", "High", "ConfigMap change not propagated to running pods",
     "Support escalation context: Updated SMTP settings ignored until manual pod restart.", "Open", "kubernetes", 5),
    ("ENG-147", "Bug", "Medium", "Init container timeout on secret mount in staging",
     "Support escalation context: Staging deploys fail intermittently; blocks QA validation.", "Open", "kubernetes", 2),
    ("ENG-148", "Bug", "High", "Ingress routing sends 10% traffic to deprecated service",
     "Support escalation context: Canary weight misconfigured; some users hit v1 API.", "In Progress", "kubernetes", 7),
    ("ENG-149", "Bug", "Medium", "CronJob cleanup task deleting active session records",
     "Support escalation context: Users logged out en masse at 03:00 UTC daily.", "Open", "kubernetes", 14),
    ("ENG-150", "Task", "Low", "Add runbook link to deploy failure alerts",
     "Support escalation context: On-call lacks context when PagerDuty fires for deploy failures.", "To Do", "kubernetes", 1),
]


def _random_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def _build_independent(
    key: str,
    issue_type: str,
    priority: str,
    summary: str,
    description: str,
    status: str,
    label: str,
    zd_count: int,
) -> dict:
    issue: dict = {
        "key": key,
        "type": issue_type,
        "priority": priority,
        "summary": summary,
        "description": description,
        "status": status,
        "assignee": random.choice(ENGINEERS),
        "reporter": random.choice(REPORTERS),
        "labels": ["support-escalation", label],
        "created": _random_date(date(2026, 5, 1), date(2026, 7, 10)),
        "zendesk_ticket_count": zd_count,
    }
    if priority in ("Urgent", "High") and random.random() < 0.7:
        arr = random.choice([45, 67, 89, 120, 156, 214, 285, 412])
        issue["arr_at_risk"] = f"${arr}K" if arr < 1000 else f"${arr:,}"
    return issue


def generate() -> list[dict]:
    issues = list(HERO_ISSUES)
    for row in INDEPENDENT_ISSUES:
        issues.append(_build_independent(*row))
    issues.sort(key=lambda i: int(i["key"].split("-")[1]))
    return issues


def main() -> None:
    random.seed(42)
    issues = generate()
    assert len(issues) == 49, f"Expected 49 issues, got {len(issues)}"
    hero_keys = {"ENG-138", "ENG-135"}
    assert sum(1 for i in issues if i.get("trigger_ticket_id")) == 2
    assert all(i["key"] in hero_keys for i in issues if i.get("trigger_ticket_id"))
    payload = {"issues": issues}
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(issues)} issues to {OUTPUT}")


if __name__ == "__main__":
    main()
