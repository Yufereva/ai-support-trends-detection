#!/usr/bin/env python3
"""Generate 20 curated, internally coherent B2B SaaS support tickets."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "golden_sample.json"
REVIEW_OUTPUT = ROOT / "golden_sample_review.md"

ACCOUNTS = [
    ("A-101", "Cedar Analytics", 72000, "AMER", "enterprise"),
    ("A-102", "Brightline Health", 48000, "AMER", "pro"),
    ("A-103", "Harbor Systems", 96000, "EMEA", "enterprise"),
    ("A-104", "Juniper Works", 24000, "APAC", "pro"),
    ("A-105", "Lattice Field", 18000, "EMEA", "pro"),
]

INTERNAL_NOTES = {
    20001: ("API Platform", "Reproduced on production gateway pgw-2. The key-rotation event was present in the control plane but missing from the gateway invalidation stream. Replayed the event and started a cache consistency review."),
    20002: ("API Platform", "Confirmed that credentials created after 08:30 UTC were absent from one production validator. Replayed the missed invalidation batch; no customer configuration change is required."),
    20003: ("Incident Commander", "Declared a production authentication incident. Traffic was shifted away from the stale validator while API Platform synchronized credential state and checked recent rotations."),
    20004: ("API Platform", "Gateway pgw-3 was drained and its credential state was resynchronized. Verification succeeds, but keep the ticket pending until the customer tests from the Terraform-managed workload."),
    20005: ("Webhook Platform", "eu-west delivery queue exceeded the autoscaling target after a traffic spike. Added workers, preserved ordering, and confirmed that no queued events were dropped."),
    20006: ("Webhook Platform", "Production delivery workers were saturated; test-delivery workers were unaffected. Scaled the production pool and monitored queue depth to zero."),
    20007: ("Incident Commander", "Opened incident INC-DEMO-27 for eu-west webhook latency. Capacity was increased and the oldest event was tracked through successful delivery."),
    20008: ("Webhook Platform", "Queue age is decreasing after capacity was added. New events are healthy; leave the case pending until the customer's final queued batch is observed."),
    20009: ("Billing Operations", "Both invoice lines reference the same seat-change event. A timed-out proration worker retried without an idempotency check. Removed the duplicate and regenerated the invoice."),
    20010: ("Billing Operations", "Paused invoice finalization, removed the duplicate credit, and regenerated the draft. Engineering work item BILL-DEMO-18 tracks idempotency on plan-change retries."),
    20011: ("Billing Operations", "Verified one storage upgrade event and two ledger adjustments. Cancelled the duplicate before collection and regenerated the invoice."),
    20012: ("Billing Operations", "Collection remains blocked. The duplicate ledger entry is removed and invoice regeneration is running; keep the support case pending until the Billing API returns one line."),
    20013: ("Identity Engineering", "SCIM directory state was correct, but the authorization invalidation consumer was stalled. Restarted the consumer, replayed events, and reviewed recent admin-group removals."),
    20014: ("Security Operations", "Revoked the contractor session and identified three stale membership entries from the same invalidation delay. Cleared them and verified that no affected session remains active."),
    20015: ("Identity Engineering", "Confirmed successful SCIM PATCH requests and stale role-evaluation data. Replayed the membership invalidation events and verified both Finance roles were removed."),
    20016: ("Identity Engineering", "Cleared the reported membership and replayed the stalled invalidation queue. Security review is still validating all group changes from the affected window."),
}

CUSTOMER_CONFIRMATIONS = {
    20001: "Confirmed. The same production request now returns 200, and we did not need to rotate the key again.",
    20002: "The new service credential is working in production now. Our old credential is no longer needed.",
    20003: "Confirmed that checkout traffic is healthy again. We see successful live requests from both regions.",
    20005: "The delayed events arrived in order, and new deliveries are consistently under thirty seconds.",
    20006: "Confirmed. The queue is empty and our receiver has all expected event IDs.",
    20007: "Warehouse automation is current again. We verified the 08:14 event and the later sequence.",
    20009: "The corrected invoice contains one adjustment and the total now matches our purchase records.",
    20010: "The regenerated draft has a single credit and the balance is correct. You can allow it to finalize.",
    20011: "We received the corrected invoice before payment, and the duplicate $860 line is gone.",
    20013: "Confirmed. The removed employee no longer has admin access, including after signing in again.",
    20014: "We tested the contractor account and two other deprovisioned users. All access is now blocked.",
    20015: "Both users have lost the Finance role. Our IdP and Northstar now show the same memberships.",
    20017: "The asynchronous export completed in three files, and our auditor can open all of them. Thank you.",
    20018: "That answers both questions. We can schedule the SDK migration without changing webhook verification.",
    20019: "The EU archive and service-account restriction meet our compliance requirement. We have what we need.",
    20020: "The confirmation shows only the sandbox add-on removed and the revised total is correct.",
}


def message(author: str, name: str, text: str, timestamp: datetime, kind: str = "public") -> dict:
    return {
        "author": author,
        "name": name,
        "text": text,
        "timestamp": timestamp.isoformat(),
        "type": kind,
    }


def ticket(
    number: int,
    created_at: str,
    subject: str,
    category: str,
    priority: str,
    status: str,
    account_index: int,
    requester: str,
    agent: str,
    channel: str,
    customer_text: str,
    agent_reply: str,
    customer_followup: str,
    agent_outcome: str,
    cluster_id: str | None,
    root_cause: str | None,
    tags: list[str],
) -> dict:
    created = datetime.fromisoformat(created_at)
    account_id, account_name, arr, region, tier = ACCOUNTS[account_index]
    messages = [
        message("customer", requester, customer_text, created),
        message("agent", agent, agent_reply, created + timedelta(minutes=38)),
        message("customer", requester, customer_followup, created + timedelta(hours=2, minutes=5)),
    ]
    internal_note = INTERNAL_NOTES.get(number)
    if internal_note:
        team, text = internal_note
        messages.append(
            message("agent", team, text, created + timedelta(hours=3), "internal")
        )
    messages.append(message("agent", agent, agent_outcome, created + timedelta(hours=4, minutes=20)))
    confirmation = CUSTOMER_CONFIRMATIONS.get(number)
    if confirmation:
        messages.append(
            message("customer", requester, confirmation, created + timedelta(hours=5, minutes=5))
        )
    return {
        "id": f"T-{number:05d}",
        "created_at": created.isoformat(),
        "subject": subject,
        "body": customer_text,
        "category": category,
        "priority": priority,
        "status": status,
        "customer_tier": tier,
        "account": {"id": account_id, "name": account_name, "arr": arr, "region": region},
        "requester": requester,
        "assignee": agent,
        "channel": channel,
        "tags": tags,
        "messages": messages,
        "ground_truth": {
            "cluster_id": cluster_id,
            "root_cause": root_cause,
            "is_trend_seed": cluster_id is not None,
        },
    }


TICKETS = [
    ticket(
        20001, "2026-07-01T08:15:00", "Production API key returns 401 after rotation",
        "api", "high", "resolved", 0, "Maya Brooks", "Daniel Cho", "email",
        "We rotated our API key this morning and now production is completely blocked. The new key works in staging, but every production request returns 401 invalid_credentials. The fingerprint ends in 7F2A. We need help quickly because our integration is down.",
        "I'm sorry this took your production integration offline. I checked fingerprint 7F2A and it is active in both environments. Please send one failed production request ID and its timestamp so I can escalate this to API Platform. Do not send the key value.",
        "Request req-demo-1048 failed at 08:42 UTC. We even created another key, and it failed the same way in production. Staging still works, so this is getting pretty frustrating.",
        "API Platform found that one production validator had missed the key-rotation update. They resynchronized it and confirmed that req-demo-1048 now returns 200. Please retry from your service before I close the case.",
        "api_key_rotation_prod_401", "Production API gateway retained stale key-validation cache entries after rotation.",
        ["api", "authentication", "production", "key-rotation"],
    ),
    ticket(
        20002, "2026-07-01T09:05:00", "New service credential rejected by production gateway",
        "api", "high", "resolved", 2, "Owen Price", "Lena Ortiz", "chat",
        "Something is wrong with credentials created after this morning's maintenance. Our new service credential works in sandbox but gets a 401 from api.northstar.example in production. Older credentials still work, but we cannot rely on them much longer.",
        "I'm sorry you're stuck using an older credential. The difference between old and newly created credentials is useful. Please share the creation timestamp and one failed request ID, and I'll have API Platform compare production validation with sandbox.",
        "The credential was created at 08:51 UTC, and request req-demo-2190 failed at 09:11 UTC. We have not changed scopes, IP allowlists, or the service account.",
        "API Platform confirmed that one production validator had missed the credential update. They replayed the update and verified the new credential. Please test the same production call again.",
        "api_key_rotation_prod_401", "Production API gateway retained stale key-validation cache entries after rotation.",
        ["api", "authentication", "production", "service-account"],
    ),
    ticket(
        20003, "2026-07-01T10:20:00", "Rotated key accepted in test but rejected in live environment",
        "api", "urgent", "resolved", 1, "Nora Singh", "Daniel Cho", "api",
        "This is urgent: our checkout integration is down. The replacement key passes the test endpoint, but live calls fail with invalid_credentials. We already revoked the previous key as part of our security process, so we have no fallback.",
        "I'm sorry this is stopping checkout. I'm treating it as a production incident: the key is active, and I've opened a priority escalation with API Platform. Please send one failed live request ID so the incident team can trace it.",
        "The latest failure is req-demo-3307 at 10:44 UTC. Customers still cannot check out. Do we need to rotate the key again, or will that just leave us in the same situation?",
        "The incident team restored consistent credential state across production and confirmed successful live requests. No second rotation is needed. Please verify checkout traffic from your side.",
        "api_key_rotation_prod_401", "Production API gateway retained stale key-validation cache entries after rotation.",
        ["api", "authentication", "production", "incident"],
    ),
    ticket(
        20004, "2026-07-01T11:10:00", "Terraform-created API key fails only on production",
        "api", "high", "pending", 3, "Eli Tan", "Lena Ortiz", "email",
        "We followed the documented Terraform flow, but the new API key is unusable in production. It works in staging, while production returns 401. The console says it is active and the scopes match the previous key. What are we missing?",
        "I'm sorry the documented flow left you with a key that doesn't work. Your scopes and active state look correct, and the staging result points to production validation. Please send one failed request ID so I can escalate a trace to API Platform.",
        "Request req-demo-4412 failed at 11:26 UTC. We can temporarily use the older key, but it expires tomorrow; please let us know when the new key is ready for another Terraform test.",
        "API Platform resynchronized the affected production validator and their verification request succeeds. I am keeping the ticket pending until you confirm the new key from the Terraform-managed workload.",
        "api_key_rotation_prod_401", "Production API gateway retained stale key-validation cache entries after rotation.",
        ["api", "authentication", "terraform", "production"],
    ),
    ticket(
        20005, "2026-07-02T07:40:00", "Webhook deliveries delayed by eighteen minutes",
        "webhooks", "high", "resolved", 4, "Sofia Marin", "Iris Cole", "chat",
        "Our webhook deliveries are suddenly 15 to 20 minutes late even though events are accepted immediately. The dashboard just shows them queued in eu-west. This is holding up customer orders.",
        "I'm sorry these delays are affecting your orders. I can confirm the events are queued on our side, not failing at your endpoint. The eu-west workers are below their normal rate, so you don't need to retry or change your receiver while I escalate this.",
        "We have had to pause fulfillment now. The newest event is eighteen minutes old, and the queue is still growing. Please treat this as urgent.",
        "Webhook Platform added eu-west worker capacity and cleared the backlog without dropping events. New deliveries are below thirty seconds. Please confirm that your order workflow received the delayed sequence.",
        "webhook_eu_worker_backlog", "EU webhook delivery workers failed to scale with a traffic spike.",
        ["webhooks", "delivery-delay", "eu-west", "queue"],
    ),
    ticket(
        20006, "2026-07-02T08:05:00", "Successful webhooks remain queued in EU region",
        "webhooks", "high", "resolved", 2, "Jonas Weber", "Iris Cole", "email",
        "Production webhooks have been pending for twelve minutes, but our endpoint is healthy and direct test deliveries arrive immediately. We have checked our receiver twice. Why are real events not moving?",
        "I'm sorry you've had to keep checking a healthy endpoint. Test deliveries take a separate path, and our telemetry confirms production events are waiting in the eu-west queue. I've escalated the queue depth and oldest-event age to Webhook Platform.",
        "The queue has jumped from 800 to 1,900 while we have been talking, and we still have no production deliveries. We need an update as soon as possible.",
        "Webhook Platform scaled the production worker pool and reports that queue depth is back to zero. Their event audit shows no drops. Please compare the delivered IDs with your receiver log.",
        "webhook_eu_worker_backlog", "EU webhook delivery workers failed to scale with a traffic spike.",
        ["webhooks", "delivery-delay", "eu-west", "queue"],
    ),
    ticket(
        20007, "2026-07-02T08:35:00", "Order events arrive long after they are created",
        "webhooks", "urgent", "resolved", 0, "Amelia Reed", "Marcus Lee", "api",
        "Our EU order events are arriving about sixteen minutes late, while US events still arrive in under a minute through the same receiver. Warehouse automation is falling behind, so this is becoming a serious operational issue.",
        "I'm sorry this is disrupting warehouse operations. The regional difference points to our EU delivery service, and telemetry shows a backlog growing since 08:00 UTC. I've opened a priority incident and will keep this case tied to it.",
        "Can you give us an estimate? The oldest missing order is from 08:14 UTC, and the warehouse team needs to know whether to switch to a manual process.",
        "The incident team cleared the backlog at 09:02 UTC and traced the 08:14 event through delivery. Please confirm that warehouse automation has processed that event and the later sequence.",
        "webhook_eu_worker_backlog", "EU webhook delivery workers failed to scale with a traffic spike.",
        ["webhooks", "delivery-delay", "eu-west", "incident"],
    ),
    ticket(
        20008, "2026-07-02T09:00:00", "EU webhook queue age keeps increasing",
        "webhooks", "high", "pending", 3, "Kenji Mori", "Marcus Lee", "chat",
        "Our EU audit-event queue is already nine minutes behind and getting worse. There are no delivery attempts in our server logs, so please do not send us through another endpoint troubleshooting checklist.",
        "You're right; this is not an endpoint rejection, and I won't ask you to repeat those checks. Our delivery log shows no attempt yet. I've added your rising queue age to the active eu-west escalation, and Webhook Platform is adding capacity.",
        "Queue age peaked at fourteen minutes and is now falling. We have received some older events but not the newest batch.",
        "Webhook Platform reports that new events are dispatching normally and the backlog is nearly clear. I am leaving this pending until you confirm receipt of the final queued batch.",
        "webhook_eu_worker_backlog", "EU webhook delivery workers failed to scale with a traffic spike.",
        ["webhooks", "delivery-delay", "eu-west", "audit-events"],
    ),
    ticket(
        20009, "2026-07-03T13:10:00", "Seat downgrade created a duplicate prorated charge",
        "billing", "high", "resolved", 1, "Grace Kim", "Ava Morgan", "email",
        "We reduced our plan from 80 to 65 seats yesterday, but today's invoice charges the same adjustment twice. That adds $1,240 we do not owe. Please fix this before anything is charged.",
        "I'm sorry we issued an invoice with a duplicate charge. I matched both lines to the same seat-change event and placed the invoice on hold, so it will not be collected while Billing Operations corrects it.",
        "Thank you for stopping the charge. Both lines have the same service period and quantity, and Finance needs a corrected invoice before Friday. Can you make sure this will not happen again on the next invoice?",
        "Billing Operations confirmed a duplicate retry, voided the extra line, and issued invoice INV-DEMO-204. Please verify the new total before we release the invoice hold.",
        "billing_duplicate_proration", "A timed-out proration job retried without an idempotency guard.",
        ["billing", "proration", "duplicate-charge", "seat-change"],
    ),
    ticket(
        20010, "2026-07-03T13:45:00", "Two identical credits appeared after plan change",
        "billing", "medium", "resolved", 4, "Theo Martin", "Ava Morgan", "chat",
        "What is going on with our draft invoice? We changed plans once, but it now shows the same proration credit twice. Please do not finalize an invoice with the wrong balance.",
        "I'm sorry the draft is wrong. I can see that both credits point to the same plan change, and I've paused finalization so the incorrect balance cannot be issued. Billing Operations is removing the duplicate now.",
        "Good, thank you for pausing it. The credits have exactly the same amount and timestamp. We should see only one credit when the new draft is ready.",
        "Billing Operations removed the duplicate credit and regenerated the draft invoice. Please review the balance; the engineering correction for retry handling is tracked separately.",
        "billing_duplicate_proration", "A timed-out proration job retried without an idempotency guard.",
        ["billing", "proration", "duplicate-credit", "plan-change"],
    ),
    ticket(
        20011, "2026-07-03T14:20:00", "Invoice repeats one mid-cycle upgrade adjustment",
        "billing", "high", "resolved", 2, "Isaac Bell", "Mina Shah", "email",
        "We made one storage upgrade, but the invoice lists the $860 adjustment twice. We cannot approve a bill that charges us twice for the same change.",
        "I'm sorry about the duplicate charge. Both lines reference the same upgrade event, and I've blocked automatic collection while Billing Operations corrects the invoice.",
        "Automatic payment is tomorrow, so we need the corrected invoice today. Our purchase order only covers the original amount, and Finance will reject anything higher.",
        "Billing Operations cancelled the duplicate adjustment and regenerated the invoice before payment. Please confirm that the corrected invoice matches your purchase order.",
        "billing_duplicate_proration", "A timed-out proration job retried without an idempotency guard.",
        ["billing", "proration", "duplicate-charge", "storage-upgrade"],
    ),
    ticket(
        20012, "2026-07-03T15:00:00", "Downgrade adjustment is listed twice on renewal invoice",
        "billing", "high", "pending", 0, "Leah Foster", "Mina Shah", "api",
        "Our renewal invoice shows the downgrade adjustment twice, and the Billing API returns two lines with the same source event and amount. This is blocking our month-end reconciliation. Please correct it urgently.",
        "I'm sorry this is holding up your reconciliation. The duplicated source event confirms there was only one change. I've blocked collection and asked Billing Operations to remove the extra ledger entry and regenerate the invoice.",
        "Thanks for pausing collection, but the API still returns both lines and Finance cannot close the account. Please let us know as soon as the corrected record is available.",
        "Billing Operations removed the duplicate ledger entry and the corrected invoice is generating. I will keep the ticket pending until you confirm that the Billing API returns one adjustment.",
        "billing_duplicate_proration", "A timed-out proration job retried without an idempotency guard.",
        ["billing", "proration", "duplicate-charge", "renewal"],
    ),
    ticket(
        20013, "2026-07-04T06:30:00", "Removed SSO group still grants admin access",
        "identity", "urgent", "resolved", 2, "Hannah Vogel", "Noah Park", "email",
        "This is a security issue. We removed an employee from Northstar-Admins in our IdP, SCIM says it succeeded, and thirty minutes later the user still has admin access. We need that access removed immediately.",
        "I'm sorry the access removal did not take effect. I verified that SCIM recorded it but the workspace role did not change. I've opened an urgent access-removal incident with Identity Engineering and will stay on the case until access is confirmed blocked.",
        "We disabled the employee in the IdP as a precaution, but Northstar still shows the admin role. This should be immediate, correct? We need confirmation that the account cannot get back in.",
        "Identity Engineering restored membership synchronization and reviewed recent admin-group removals in your workspace. Removal should be immediate; please test the employee account once more.",
        "scim_group_cache_stale", "The authorization service did not invalidate cached SCIM group memberships.",
        ["sso", "scim", "access-removal", "security"],
    ),
    ticket(
        20014, "2026-07-04T07:05:00", "SCIM deprovisioned user remains signed in",
        "identity", "urgent", "resolved", 0, "Caleb Ross", "Noah Park", "chat",
        "We deactivated a contractor, but they can still open the admin dashboard with an existing session even though SCIM returned 200. This is unacceptable for a deprovisioned account. Please revoke access now.",
        "You're right to treat this as urgent, and I'm sorry the session remained active. The directory shows the contractor as deprovisioned. I've opened a Security Operations case to revoke the session immediately and check related removals.",
        "The session still opens the dashboard. We deprovisioned two other users this morning too, so please check them as well. We need to know the scope of this issue.",
        "Security Operations revoked the session and reviewed deprovision events from the affected period. They found and removed three stale memberships. Please test the contractor and the other recent removals.",
        "scim_group_cache_stale", "The authorization service did not invalidate cached SCIM group memberships.",
        ["sso", "scim", "deprovisioning", "security"],
    ),
    ticket(
        20015, "2026-07-04T07:40:00", "IdP group removal not reflected in workspace roles",
        "identity", "high", "resolved", 3, "Rina Sato", "Priya Nair", "api",
        "We removed two users from the Finance group, but both still have the Finance role in Northstar even though the SCIM PATCH requests succeeded. They can see sensitive financial data they should no longer have.",
        "I'm sorry those permissions remained in place. I confirmed both SCIM requests succeeded while the workspace roles stayed unchanged. I've escalated the request IDs and affected users to Identity Engineering as a high-priority access issue.",
        "We signed both users out manually, but their roles did not change. We have disabled the accounts in the IdP for now. Please tell us when it is safe to re-enable them.",
        "Identity Engineering replayed the delayed membership updates and verified that both Finance roles were removed. Please compare the workspace roles with your IdP once more.",
        "scim_group_cache_stale", "The authorization service did not invalidate cached SCIM group memberships.",
        ["sso", "scim", "group-sync", "workspace-roles"],
    ),
    ticket(
        20016, "2026-07-04T08:15:00", "Role persists after SCIM group membership deletion",
        "identity", "high", "pending", 1, "Marcus Hill", "Priya Nair", "email",
        "SCIM deleted a user's Operations membership at 07:42 UTC, but Northstar still gives them the Operations role. There were no SCIM errors. We cannot tell whether this is one user or a wider access problem.",
        "I'm sorry the role was not removed as expected. I confirmed the directory deletion and the unchanged Northstar role. I've escalated this user and the 07:42 request to Identity Engineering, including a review of other membership changes from the same window.",
        "The Operations role is still there. Please check the other changes from this morning too; we do not want to discover another user still has access later.",
        "Identity Engineering replayed the delayed updates and the reported role is gone. I am keeping this pending while Security Operations verifies all memberships from the affected window.",
        "scim_group_cache_stale", "The authorization service did not invalidate cached SCIM group memberships.",
        ["sso", "scim", "group-sync", "authorization-cache"],
    ),
    ticket(
        20017, "2026-07-05T09:00:00", "How can we export more than 100,000 audit events?",
        "exports", "low", "resolved", 4, "Mila Stone", "Evan Grant", "chat",
        "I'm trying to export a full quarter of audit events for an external review, but the screen stops at 100,000 rows. Is there another way to get everything without splitting the dates by hand?",
        "Yes, you can avoid splitting the dates manually. The Audit Export API runs the export in the background and gives you a download link when it is ready; the 100,000-row UI limit does not apply.",
        "Perfect. Will it split a very large export into manageable files, and how long do we have to download them?",
        "It splits automatically at one million rows, and each signed download link works for 24 hours. I've also sent you an example using your quarter's date range.",
        None, None, ["audit-log", "export", "how-to"],
    ),
    ticket(
        20018, "2026-07-05T10:20:00", "Python SDK v2 migration timeline",
        "sdk", "medium", "resolved", 3, "Arun Mehta", "Evan Grant", "email",
        "We're planning our Python SDK upgrade and need to budget the work. When does v1 stop receiving security fixes, and is there a practical migration guide for the v2 pagination changes?",
        "You have until December 31, 2026 for SDK v1 security fixes. The v2 guide includes a cursor-pagination adapter, so your team can migrate one client module at a time instead of changing everything at once.",
        "That makes the timeline much easier. Do we also need to rewrite our webhook signature verification during the upgrade?",
        "No, webhook signature verification stays the same. I've linked the pagination guide and the compatibility matrix for Python 3.10 through 3.13 so your team can plan the remaining changes.",
        None, None, ["sdk", "python", "migration", "how-to"],
    ),
    ticket(
        20019, "2026-07-05T11:10:00", "Audit log retention for enterprise workspaces",
        "account", "low", "resolved", 0, "Daria Wells", "Sam Rivera", "email",
        "Our compliance review is next month, and we need a clear answer on audit retention. Does Enterprise include twelve months, and is there an option to keep records for seven years?",
        "Enterprise includes twelve months of searchable audit events. For seven-year retention, the compliance archive add-on copies events to encrypted object storage. I can help you confirm whether it fits your review requirements.",
        "The main requirements are EU storage and access limited to one compliance service account. Can the archive support both?",
        "Yes, both are supported: you can select EU storage and restrict archive access to a dedicated read-only service account. I've sent the configuration checklist for your compliance team.",
        None, None, ["audit-log", "retention", "compliance", "how-to"],
    ),
    ticket(
        20020, "2026-07-05T12:00:00", "Cancel unused sandbox add-on at renewal",
        "account", "low", "resolved", 1, "Ben Carter", "Sam Rivera", "chat",
        "We don't use the extra sandbox anymore and want it removed at our August renewal. Please make sure this does not cancel or change our main enterprise workspace.",
        "I found the sandbox add-on on contract DEMO-42. I can remove only that add-on on the renewal date; your primary workspace and seat count will stay exactly as they are.",
        "Yes, please go ahead. Send me something in writing with the new total so I can give it to Finance.",
        "Done. The sandbox add-on is scheduled to end on August 1, and I've sent confirmation with the revised total. Your production workspace and seats were not changed.",
        None, None, ["account", "add-on", "cancellation", "renewal"],
    ),
]


def validate(tickets: list[dict]) -> None:
    assert len(tickets) == 20
    assert len({item["id"] for item in tickets}) == 20
    assert all(item["id"].startswith("T-") and len(item["id"]) == 7 for item in tickets)
    assert all(item["body"] == item["messages"][0]["text"] for item in tickets)
    assert all(5 <= len(item["messages"]) <= 6 for item in tickets)
    assert all(
        item["messages"] == sorted(item["messages"], key=lambda msg: msg["timestamp"])
        for item in tickets
    )
    assert all(
        item["messages"][-1]["author"] == ("customer" if item["status"] == "resolved" else "agent")
        for item in tickets
    )
    assert all(
        sum(msg["type"] == "internal" for msg in item["messages"])
        == (1 if item["ground_truth"]["cluster_id"] else 0)
        for item in tickets
    )
    trend_tickets = [item for item in tickets if item["ground_truth"]["cluster_id"]]
    assert all(
        any(
            acknowledgement in item["messages"][1]["text"].lower()
            for acknowledgement in ("sorry", "you're right")
        )
        for item in trend_tickets
    )
    assert len({item["messages"][1]["text"].split(".", 1)[0] for item in tickets}) == 20
    banned_support_actions = (
        "we flushed",
        "we scaled",
        "we drained",
        "i am routing traffic",
        "i am invalidating",
        "i am revoking",
        "i have cleared this user",
    )
    public_agent_text = " ".join(
        msg["text"].lower()
        for item in tickets
        for msg in item["messages"]
        if msg["author"] == "agent" and msg["type"] == "public"
    )
    assert not any(phrase in public_agent_text for phrase in banned_support_actions)
    clusters: dict[str, int] = {}
    unrelated = 0
    for item in tickets:
        cluster_id = item["ground_truth"]["cluster_id"]
        if cluster_id is None:
            unrelated += 1
        else:
            clusters[cluster_id] = clusters.get(cluster_id, 0) + 1
    assert sorted(clusters.values()) == [4, 4, 4, 4]
    assert unrelated == 4


def build_review(tickets: list[dict]) -> str:
    lines = [
        "# Golden Sample Review",
        "",
        "All content is synthetic. Review each conversation before scaling the dataset.",
        "",
    ]
    for item in tickets:
        ground_truth = item["ground_truth"]
        lines.extend(
            [
                f"## {item['id']} - {item['subject']}",
                "",
                f"- Category: `{item['category']}`",
                f"- Priority / status: `{item['priority']}` / `{item['status']}`",
                f"- Account: {item['account']['name']} ({item['customer_tier']}, {item['account']['region']})",
                f"- Expected cluster: `{ground_truth['cluster_id'] or 'unrelated'}`",
                f"- Root cause: {ground_truth['root_cause'] or 'None; isolated support request.'}",
                "",
            ]
        )
        for msg in item["messages"]:
            if msg["type"] == "internal":
                role = "Internal note"
            else:
                role = "Customer" if msg["author"] == "customer" else "Agent"
            lines.extend([f"**{role} - {msg['name']}**", "", msg["text"], ""])
        lines.extend(["---", ""])
    return "\n".join(lines)


def main() -> None:
    validate(TICKETS)
    payload = {
        "dataset": "northstar-cloud-support-v2-golden-sample",
        "version": "0.1.0",
        "synthetic": True,
        "ticket_count": len(TICKETS),
        "tickets": TICKETS,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    REVIEW_OUTPUT.write_text(build_review(TICKETS), encoding="utf-8")
    print(f"Wrote {len(TICKETS)} curated tickets to {OUTPUT}")
    print(f"Wrote human review to {REVIEW_OUTPUT}")


if __name__ == "__main__":
    main()
