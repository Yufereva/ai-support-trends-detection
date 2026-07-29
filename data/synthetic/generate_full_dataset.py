#!/usr/bin/env python3
"""Generate the deterministic 1,500-ticket Northstar Cloud dataset."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
GOLDEN_PATH = ROOT / "golden_sample.json"
SCHEMA_PATH = ROOT / "ticket-schema-v2.json"
OUTPUT_PATH = ROOT / "full_dataset.json"
TARGET_TICKET_COUNT = 1500
GOLDEN_TICKET_COUNT = 20
TREND_VARIANTS_PER_CLUSTER = 20

ACCOUNTS = [
    ("A-201", "Atlas Grove", 84000, "AMER", "enterprise"),
    ("A-202", "Blue Oak Labs", 36000, "EMEA", "pro"),
    ("A-203", "Copper Finch", 62000, "APAC", "enterprise"),
    ("A-204", "Delta Harbor", 27000, "AMER", "pro"),
    ("A-205", "Evergreen Logic", 110000, "EMEA", "enterprise"),
    ("A-206", "Fathom Retail", 42000, "APAC", "pro"),
    ("A-207", "Granite Health", 93000, "AMER", "enterprise"),
    ("A-208", "Helio Works", 21000, "EMEA", "pro"),
    ("A-209", "Indigo Freight", 57000, "APAC", "enterprise"),
    ("A-210", "Juniper Data", 33000, "AMER", "pro"),
    ("A-211", "Kiteframe", 76000, "EMEA", "enterprise"),
    ("A-212", "Lumen Ridge", 19000, "APAC", "pro"),
    ("A-213", "Meridian Foods", 68000, "AMER", "enterprise"),
    ("A-214", "Northwind Bio", 46000, "EMEA", "pro"),
    ("A-215", "Orchid Systems", 88000, "APAC", "enterprise"),
    ("A-216", "Pinecone Media", 25000, "AMER", "pro"),
]

REQUESTERS = [
    "Alex Chen", "Brooke Ellis", "Carmen Ruiz", "Dev Patel", "Elena Novak",
    "Felix Wong", "Gia Romano", "Hugo Larsen", "Imani Cole", "Jack Turner",
    "Keira Shah", "Luis Moreno", "Mei Park", "Nadia Petrova", "Omar Haddad",
    "Paula Green", "Quinn Baker", "Ravi Menon", "Sara Lind", "Tom Becker",
]
AGENTS = ["Ava Morgan", "Daniel Cho", "Iris Cole", "Lena Ortiz", "Marcus Lee", "Mina Shah", "Noah Park", "Priya Nair"]
CHANNELS = ["email", "chat", "api"]

# Irregular arrival times keep the demo queue realistic while remaining reproducible.
NORMAL_OPEN_OFFSETS_HOURS = [
    0, 2, 5, 9, 11, 14, 18, 22, 25, 27, 31, 35, 38, 41, 43, 48,
    51, 55, 58, 61, 65, 67, 70, 74, 77, 82, 84, 88, 91, 94, 96, 99,
]
TREND_SUBJECT_PREFIXES = [
    "",
    "Primary workspace: ",
    "After configuration change: ",
    "Production blocked: ",
]
BASELINE_WORKSTREAMS = [
    "production rollout",
    "security review",
    "secondary workspace",
    "EU deployment",
    "compliance audit",
    "automation project",
    "finance workflow",
    "migration program",
    "sandbox test",
    "customer onboarding",
    "regional expansion",
]
BASELINE_STAGES = [
    "planning",
    "validation",
    "documentation",
    "pilot testing",
    "pre-launch checks",
    "administrator review",
    "renewal review",
    "integration testing",
]

TREND_SPECS = {
    "api_key_rotation_prod_401": {
        "category": "api", "team": "API Platform", "root": "Production API gateway retained stale key-validation cache entries after rotation.",
        "tags": ["api", "authentication", "production", "key-rotation"],
        "subjects": ["Rotated API key rejected in production", "New credential returns 401 on live API", "Production does not accept replacement key", "Fresh service key works only in staging", "API rotation left production authentication broken"],
        "symptoms": ["The replacement key works in staging, but production returns 401 invalid_credentials.", "A newly created credential is accepted by sandbox and rejected by the live gateway.", "The console marks our rotated key active, yet every production call fails authentication.", "Old credentials work in production while the new key is refused.", "Our test request succeeds, but the identical live request reports an invalid credential."],
        "impacts": ["Our customer integration is down and we need this investigated urgently.", "We followed the rotation guide and cannot safely return to the revoked key.", "Deployments are blocked until the live gateway accepts the credential.", "This has stopped production traffic even though our scopes are unchanged."],
        "acks": ["I'm sorry the rotation left production blocked.", "I understand why a key that works only in staging is not usable.", "I'm sorry your live integration is failing after a documented rotation.", "You're right to escalate this as a production authentication issue."],
        "evidence": ["The failed request is {request_id} at {clock} UTC; the key is active in the console.", "Request {request_id} failed at {clock} UTC, and no scopes or allowlists changed.", "The latest 401 is {request_id} at {clock} UTC; a second key behaved the same way.", "Trace {request_id} failed at {clock} UTC while its staging equivalent returned 200.", "We reproduced it with request {request_id} at {clock} UTC and still have no production fallback."],
        "internal": ["Found the rotation event missing from one production validator and replayed it.", "Confirmed stale credential state on a live gateway and resynchronized the validator.", "Drained the outdated validator, replayed the invalidation batch, and verified the request trace.", "Compared control-plane and gateway state; restored the missed key update."],
        "outcome": ["API Platform restored the missing credential update and verified {request_id} successfully.", "The affected production validator has been resynchronized and now accepts the new key.", "API Platform corrected stale gateway state; no second rotation or scope change is required.", "The incident team restored consistent key state across production and confirmed a 200 response."],
        "confirm": ["Confirmed, production requests are succeeding again.", "The new credential works now and we no longer need the old key.", "Our deployment passed the live authentication check. Thank you for staying on this.", "We retried from both regions and the 401 errors are gone."],
    },
    "webhook_eu_worker_backlog": {
        "category": "webhooks", "team": "Webhook Platform", "root": "EU webhook delivery workers failed to scale with a traffic spike.",
        "tags": ["webhooks", "delivery-delay", "eu-west", "queue"],
        "subjects": ["EU webhooks are arriving late", "Production events stuck in eu-west queue", "Webhook queue age keeps increasing", "Order events delayed in EU workspace", "No delivery attempts for queued EU events"],
        "symptoms": ["Events are accepted immediately but reach our endpoint more than fifteen minutes later.", "Production deliveries remain pending while direct test webhooks arrive normally.", "The eu-west queue age is rising and there are no attempts in our receiver logs.", "EU order events are delayed while US events using the same endpoint arrive on time.", "The dashboard shows a growing queue even though our endpoint health is green."],
        "impacts": ["Customer orders are waiting on these events and fulfillment is paused.", "Our automation is falling behind and the operations team needs an estimate.", "We have checked our receiver twice; this appears to be on the delivery side.", "The oldest missing event is blocking a time-sensitive workflow."],
        "acks": ["I'm sorry the delivery delay is holding up your workflow.", "You're right that successful test events rule out the usual endpoint issue.", "I'm sorry your team has had to pause work while events remain queued.", "I understand why the regional difference points to our EU service."],
        "evidence": ["The oldest event is {request_id} from {clock} UTC and has no delivery attempt.", "Queue item {request_id} has been pending since {clock} UTC.", "Event {request_id} entered the queue at {clock} UTC and is still missing.", "Our receiver last saw event {request_id}; the next event was expected at {clock} UTC.", "The queue reached {count} events after {request_id} was accepted at {clock} UTC."],
        "internal": ["Added eu-west delivery workers and tracked the oldest queued event through delivery.", "Production workers were saturated; scaled capacity and verified that ordering was preserved.", "Attached the case to the regional incident, increased capacity, and monitored queue age to zero.", "Confirmed no endpoint attempts were made; cleared the worker backlog without dropping events."],
        "outcome": ["Webhook Platform cleared the eu-west backlog and traced {request_id} through delivery.", "Additional workers returned queue age to normal, and no events were dropped.", "The regional incident is mitigated; new deliveries are below thirty seconds.", "Webhook Platform restored normal dispatch and verified the delayed event sequence."],
        "confirm": ["The missing events arrived in order and new deliveries are on time.", "Our queue is current again and the workflow has resumed.", "Confirmed, we received the delayed event and everything after it.", "The receiver now has every expected event ID. Thank you."],
    },
    "billing_duplicate_proration": {
        "category": "billing", "team": "Billing Operations", "root": "A timed-out proration job retried without an idempotency guard.",
        "tags": ["billing", "proration", "duplicate-charge", "invoice"],
        "subjects": ["Invoice contains duplicate proration line", "Plan change adjustment appears twice", "Duplicate credit on draft invoice", "Renewal bill repeats one adjustment", "One account change created two invoice entries"],
        "symptoms": ["We changed our plan once, but the invoice shows the same prorated charge twice.", "Two identical credits appeared after a single subscription update.", "The Billing API returns duplicate lines with one source event and amount.", "Our renewal invoice repeats a downgrade adjustment even though there was one request.", "A mid-cycle upgrade produced two matching entries on the draft invoice."],
        "impacts": ["Please stop collection because Finance will not approve the incorrect total.", "This is blocking month-end reconciliation and needs to be corrected today.", "We do not want the draft finalized with a balance that is clearly wrong.", "Automatic payment is approaching and our purchase order covers only one adjustment."],
        "acks": ["I'm sorry we produced an invoice with a duplicate adjustment.", "You're right to stop this before the incorrect balance is finalized.", "I'm sorry this billing error is blocking your Finance team.", "I understand why two lines for one change cannot be approved."],
        "evidence": ["Both lines reference event {request_id} and have the same timestamp.", "The duplicate entries for {request_id} use the same service period and quantity.", "Billing event {request_id} appears twice in the API response.", "The two adjustments tied to {request_id} are identical down to the amount.", "Invoice source {request_id} is the only plan change we submitted."],
        "internal": ["Blocked collection, removed the duplicate ledger entry, and regenerated the invoice.", "Matched both lines to one retry, voided the duplicate, and opened an idempotency work item.", "Paused finalization and rebuilt the draft from the single valid plan-change event.", "Cancelled the duplicated proration entry before payment and verified the revised total."],
        "outcome": ["Billing Operations removed the duplicate and regenerated the invoice from the valid event.", "The incorrect line was voided and automatic collection remains paused for your review.", "Billing Operations rebuilt the draft with one adjustment and confirmed the new total.", "The duplicate entry is gone; the retry-handling correction is tracked separately."],
        "confirm": ["The corrected invoice has one adjustment and the total is right.", "Finance approved the regenerated draft. You can release the hold.", "The duplicate is gone from the API response, so reconciliation can continue.", "We received the revised invoice before payment and it matches our purchase order."],
    },
    "scim_group_cache_stale": {
        "category": "identity", "team": "Identity Engineering", "root": "The authorization service did not invalidate cached SCIM group memberships.",
        "tags": ["sso", "scim", "access-removal", "security"],
        "subjects": ["Removed SCIM user still has workspace role", "IdP group removal did not revoke access", "Deprovisioned account remains signed in", "Workspace role persists after SCIM update", "Successful SCIM removal not reflected in permissions"],
        "symptoms": ["SCIM reports a successful group removal, but the user still has the workspace role.", "Our IdP deactivated the account while an existing Northstar session remains active.", "Two users removed from a sensitive group can still see the same permissions.", "The directory membership is gone, but Northstar continues to grant access.", "A successful SCIM PATCH has not changed the user's authorization."],
        "impacts": ["This is a security issue and we need access revoked immediately.", "We disabled the account as a precaution but need the Northstar session checked now.", "The role exposes sensitive data, so please treat this as urgent.", "We also need to know whether other removals from this morning are delayed."],
        "acks": ["I'm sorry the access removal did not take effect.", "You're right to treat an active deprovisioned session as urgent.", "I'm sorry those permissions remained after a successful SCIM update.", "I understand why you need both this account and related removals checked."],
        "evidence": ["The SCIM request is {request_id} at {clock} UTC, and the role is still visible.", "Audit entry {request_id} succeeded at {clock} UTC, but signing out did not remove the role.", "The affected membership was deleted in {request_id} at {clock} UTC.", "Request {request_id} returned 200 at {clock} UTC while the existing session kept access.", "The IdP completed removal {request_id} at {clock} UTC with no errors."],
        "internal": ["Restarted the stalled invalidation consumer, replayed membership events, and reviewed related removals.", "Revoked the active session and cleared stale authorization entries from the affected window.", "Confirmed directory state, replayed delayed group updates, and verified role removal.", "Cleared the reported membership and started a broader security review of recent changes."],
        "outcome": ["Identity Engineering replayed the delayed update and verified that the role is removed.", "Security Operations revoked the session and checked related deprovisioning events.", "The stale membership is cleared, and recent group removals were reviewed for the same delay.", "Identity Engineering restored synchronization and confirmed that access is now blocked."],
        "confirm": ["Confirmed, the user no longer has the role after signing in again.", "We tested the account and access is fully blocked now.", "The IdP and Northstar memberships match again for the affected users.", "The sensitive role is gone. Thank you for checking the other removals too."],
    },
}

BASELINE_TOPICS = [
    ("audit_export", "exports", ["audit-log", "export"], "Exporting a large audit history", "We need a full audit period, but the UI export limit is too small. Is there a background export?", "Use the Audit Export API; it runs asynchronously and provides signed download links."),
    ("sdk_migration", "sdk", ["sdk", "migration"], "Planning a Python SDK v2 migration", "When does SDK v1 support end, and can we migrate pagination one module at a time?", "Security fixes continue through December 31, 2026, and the cursor adapter supports a staged migration."),
    ("audit_retention", "account", ["audit-log", "retention"], "Audit retention options", "Our compliance team needs more than twelve months of audit records. What archive options are available?", "Enterprise includes twelve searchable months; the compliance archive supports encrypted retention for up to seven years."),
    ("sandbox_cancel", "account", ["account", "cancellation"], "Removing an unused sandbox add-on", "We want to remove an extra sandbox at renewal without changing our production workspace.", "The sandbox add-on can end at renewal while the primary workspace and seats remain unchanged."),
    ("api_pagination", "api", ["api", "pagination"], "Cursor pagination for API results", "Our results stop after the first page. How should we follow the next cursor safely?", "Read next_cursor from each response and pass it unchanged until the API returns null."),
    ("rate_limits", "api", ["api", "rate-limit"], "Understanding API rate limits", "We are planning a batch job and need to know the request limit and retry behavior.", "Use the rate-limit headers and exponential backoff with jitter when the API returns 429."),
    ("webhook_signatures", "webhooks", ["webhooks", "security"], "Verifying webhook signatures", "Which bytes should we sign, and can we rotate the webhook secret without downtime?", "Verify the raw request body and keep both secrets active during the documented rotation window."),
    ("webhook_retries", "webhooks", ["webhooks", "retries"], "Webhook retry schedule", "What retry schedule applies after our endpoint returns a temporary 503?", "Northstar retries with exponential delays and shows each attempt in the delivery log."),
    ("invoice_recipient", "billing", ["billing", "invoice"], "Changing the invoice recipient", "Finance needs future invoices sent to a shared billing address instead of the account owner.", "A billing admin can update the invoice recipient without changing workspace ownership."),
    ("tax_document", "billing", ["billing", "tax"], "Downloading tax documents", "Where can our Finance team download the annual tax invoice and payment receipt?", "Billing admins can download both documents from Billing history for each completed payment."),
    ("saml_certificate", "identity", ["sso", "saml"], "Rotating a SAML certificate", "Our IdP signing certificate expires soon. Can we upload the replacement before the cutover?", "Upload the secondary certificate first, test SSO, then promote it during the maintenance window."),
    ("scim_setup", "identity", ["scim", "setup"], "Setting up SCIM provisioning", "We are enabling SCIM and need the correct base URL, token scope, and test sequence.", "Create a provisioning token, use the workspace SCIM base URL, and test with one pilot group first."),
    ("data_residency", "account", ["account", "data-residency"], "EU data residency availability", "Can a new enterprise workspace keep primary customer data and backups in the EU?", "EU residency is available for eligible enterprise workspaces and includes regional backups."),
    ("user_invites", "account", ["account", "users"], "Inviting users in bulk", "We need to add a project team without sending invitations one address at a time.", "Workspace admins can upload the documented CSV template or provision the group through SCIM."),
    ("export_format", "exports", ["export", "format"], "Choosing JSON or CSV export format", "Does the activity export preserve nested metadata, or should we request JSON instead of CSV?", "JSON preserves nested metadata; CSV flattens common fields for spreadsheet workflows."),
    ("sdk_compatibility", "sdk", ["sdk", "compatibility"], "Supported Python versions", "Which Python versions are supported by the current Northstar SDK release?", "The current SDK supports Python 3.10 through 3.13; older runtimes require the maintained v1 line."),
]

OPEN_ALTERNATE_SCENARIOS = {
    "audit_export": ("Scheduling audit exports to cloud storage", "Can we send a nightly audit export directly to our cloud storage bucket instead of downloading it manually?", "Create a scheduled Audit Export job and configure its signed output for your storage automation."),
    "sdk_migration": ("Node.js SDK v2 migration timeline", "Does the Node.js SDK follow the same v1 retirement date, and is there a compatibility guide for middleware?", "The Node.js v1 line follows the published retirement schedule, and the migration guide covers middleware and pagination changes."),
    "audit_retention": ("Placing audit events under legal hold", "Can selected audit events be retained beyond our standard policy while a legal review is active?", "The compliance archive supports scoped legal holds without changing the workspace-wide searchable retention period."),
    "sandbox_cancel": ("Pausing a sandbox between test cycles", "Can we suspend a sandbox for two months and reactivate it later without deleting its configuration?", "Sandboxes cannot be paused, but Support can outline export and recreation options before the next billing period."),
    "api_pagination": ("Duplicate records while paging through the API", "Our sync sees a few records twice when data changes between cursor requests. How should we avoid duplicates?", "Use the stable record ID for deduplication and keep the server cursor unchanged throughout each pagination run."),
    "rate_limits": ("Rate limits for separate service accounts", "Do two service accounts in the same workspace receive separate API quotas or share one workspace limit?", "Service accounts share the workspace quota, while the response headers show the remaining capacity for the active window."),
    "webhook_signatures": ("Webhook signature mismatch behind our proxy", "Signature checks fail after our proxy decompresses the request body, although direct deliveries verify correctly.", "Capture and verify the original raw request bytes before decompression or other proxy transformations."),
    "webhook_retries": ("Replaying one failed webhook delivery", "Can we replay a single failed event after fixing our endpoint without retrying the whole batch?", "Use the delivery log to replay the individual event; the replay receives a new attempt ID and preserves the event ID."),
    "invoice_recipient": ("Using separate billing and renewal contacts", "Can invoices go to Accounts Payable while renewal notices continue to the workspace owner?", "Billing admins can set a dedicated invoice recipient without changing the owner who receives renewal notices."),
    "tax_document": ("Company tax ID missing from an invoice", "Our latest invoice does not show the VAT ID saved in the billing profile. Can the document be regenerated?", "After the billing profile is corrected, Billing Support can regenerate an eligible invoice with the updated tax details."),
    "saml_certificate": ("Refreshing SAML metadata after an IdP change", "Our IdP metadata URL now serves a new signing certificate. Does Northstar refresh it automatically?", "Northstar does not replace an active certificate automatically; upload and test the new certificate before promotion."),
    "scim_setup": ("Mapping a pilot group during SCIM rollout", "Can we provision one pilot group first without synchronizing every user assigned to the SCIM application?", "Limit the IdP assignment to the pilot group, validate its attribute mapping, and expand the assignment after testing."),
    "data_residency": ("Moving an existing workspace to EU residency", "Our workspace was created in the US. Is there a supported migration path to EU data residency?", "Eligible enterprise workspaces require a planned regional migration; the account team can start the readiness review."),
    "user_invites": ("Invitation emails are not reaching new users", "Three invited users appear as pending, but none received an email and the resend option made no difference.", "Confirm the addresses and mail filtering first, then use the invitation delivery IDs so Support can trace the messages."),
    "export_format": ("Preserving timestamp precision in CSV exports", "Our CSV export rounds event timestamps, but the API response includes milliseconds. Can the export retain them?", "JSON retains the full timestamp precision; CSV uses the standardized display format for spreadsheet compatibility."),
    "sdk_compatibility": ("Node.js runtime support for the current SDK", "Which Node.js LTS versions are supported by the latest Northstar SDK in production?", "The current Node.js SDK supports the active LTS releases listed in the compatibility matrix; older runtimes remain on the maintained v1 line."),
}

CONTEXTS = [
    "This is for our production rollout next week.",
    "Our internal review is waiting on a clear answer.",
    "We are testing this first in a non-production workspace.",
    "The operations team needs to document the process.",
    "We want to avoid an unnecessary manual workaround.",
]
CONFIRMATIONS = [
    "That answers the question and gives us a clear next step. Thank you.",
    "Understood. We tested the documented approach and it works for us.",
    "Perfect, that is the information our team needed.",
    "Thanks. We can proceed without changing the rest of our setup.",
    "The example is clear and our team has added it to the rollout plan.",
]
PENDING_QUESTIONS = [
    "That helps, but can you confirm whether the same guidance applies to our secondary workspace?",
    "Before we proceed, could you check whether our current plan includes this option?",
    "Can you also verify this against our workspace configuration so we do not disrupt production?",
    "We need one account-specific detail confirmed before the team can move forward.",
    "Could you send the exact documentation link and confirm that no admin setting must change first?",
]
PENDING_RESPONSES = [
    "Yes. I'm checking the secondary workspace now and will update this case with the result.",
    "I'm confirming plan eligibility with the account team and will reply here before you proceed.",
    "I've requested a configuration review and will keep the ticket pending until that check is complete.",
    "I have the account-specific question with our specialist and will post the confirmed answer here.",
    "I'm verifying the prerequisite and will send the exact documentation in the next update.",
]


def msg(author: str, name: str, text: str, when: datetime, kind: str = "public") -> dict:
    return {"author": author, "name": name, "text": text, "timestamp": when.isoformat(), "type": kind}


def account_for(index: int) -> tuple[str, str, int, str, str]:
    return ACCOUNTS[index % len(ACCOUNTS)]


def envelope(index: int, when: datetime, subject: str, body: str, category: str, priority: str, status: str, tags: list[str], messages: list[dict], ground_truth: dict) -> dict:
    account_id, account_name, arr, region, tier = account_for(index)
    return {
        "id": f"T-{20100 + index:05d}", "created_at": when.isoformat(), "subject": subject,
        "body": body, "category": category, "priority": priority, "status": status,
        "customer_tier": tier, "account": {"id": account_id, "name": account_name, "arr": arr, "region": region},
        "requester": REQUESTERS[index % len(REQUESTERS)], "assignee": AGENTS[index % len(AGENTS)],
        "channel": CHANNELS[index % len(CHANNELS)], "tags": tags, "messages": messages,
        "ground_truth": ground_truth,
    }


def build_trend_ticket(index: int, cluster_id: str, variant: int) -> dict:
    spec = TREND_SPECS[cluster_id]
    base_day = {"api_key_rotation_prod_401": 0, "webhook_eu_worker_backlog": 1, "billing_duplicate_proration": 2, "scim_group_cache_stale": 3}[cluster_id]
    when = datetime(2026, 7, 1, 6) + timedelta(days=base_day, minutes=variant * 83)
    requester = REQUESTERS[index % len(REQUESTERS)]
    agent = AGENTS[index % len(AGENTS)]
    request_id = f"demo-{cluster_id.split('_')[0]}-{variant + 5100}"
    clock = (when + timedelta(minutes=17)).strftime("%H:%M")
    count = 700 + variant * 61
    base_subject = spec["subjects"][variant % 5]
    prefix = TREND_SUBJECT_PREFIXES[variant // 5]
    subject = base_subject if not prefix else prefix + base_subject.lower()
    body = f"{spec['symptoms'][variant % 5]} {spec['impacts'][variant // 5]}"
    evidence = spec["evidence"][variant % 5].format(request_id=request_id, clock=clock, count=count)
    messages = [
        msg("customer", requester, body, when),
        msg("agent", agent, f"{spec['acks'][variant % 4]} Please send one affected ID and timestamp; I'll attach them to the {spec['team']} escalation.", when + timedelta(minutes=31)),
        msg("customer", requester, evidence, when + timedelta(hours=1, minutes=22)),
        msg("agent", spec["team"], spec["internal"][variant % 4], when + timedelta(hours=2, minutes=4), "internal"),
    ]
    open_ticket = variant % 5 == 3
    pending = variant % 5 == 4
    outcome = spec["outcome"][variant % 4].format(request_id=request_id)
    if open_ticket or pending:
        next_step = (
            "I'm keeping this open while we monitor the next production event."
            if open_ticket
            else "I'm keeping this pending until you verify the result from your environment."
        )
        messages.append(msg("agent", agent, f"{outcome} {next_step}", when + timedelta(hours=3, minutes=11)))
    else:
        messages.append(msg("agent", agent, f"{outcome} Please test once more before I close the case.", when + timedelta(hours=3, minutes=11)))
        messages.append(msg("customer", requester, spec["confirm"][variant % 4], when + timedelta(hours=4)))
    return envelope(
        index, when, subject, body, spec["category"],
        "urgent" if variant % 7 == 0 else "high",
        "open" if open_ticket else "pending" if pending else "resolved",
        spec["tags"], messages,
        {"cluster_id": cluster_id, "topic_id": cluster_id, "is_emerging_trend": True, "root_cause": spec["root"], "is_trend_seed": True},
    )


def build_baseline_ticket(index: int, topic_index: int, variant: int, variant_count: int) -> dict:
    topic_id, category, tags, subject, question, answer = BASELINE_TOPICS[topic_index]
    def created_at(candidate: int) -> datetime:
        return datetime(2024, 7, 1, 9) + timedelta(
            days=(candidate * 17 + topic_index * 31) % 700,
            hours=(candidate * 3 + topic_index) % 8,
        )

    open_variants = sorted(
        (candidate for candidate in range(variant_count) if candidate % 5 != 4),
        key=created_at,
        reverse=True,
    )[:2]
    open_ticket = variant in open_variants
    open_slot = open_variants.index(variant) if open_ticket else None
    pending = variant % 5 == 4
    if open_slot == 0:
        subject, question, answer = OPEN_ALTERNATE_SCENARIOS[topic_id]
    elif open_slot is None:
        workstream = BASELINE_WORKSTREAMS[variant % len(BASELINE_WORKSTREAMS)]
        stage = BASELINE_STAGES[(variant // len(BASELINE_WORKSTREAMS)) % len(BASELINE_STAGES)]
        subject = f"{subject} - {workstream} {stage}"

    when = created_at(variant)
    requester = REQUESTERS[index % len(REQUESTERS)]
    agent = AGENTS[index % len(AGENTS)]
    if open_ticket:
        context = CONTEXTS[variant % len(CONTEXTS)]
    else:
        context = f"This question came up during our {workstream} {stage}."
    body = f"{question} {context} Reference: demo-help-{topic_index + 1}-{variant + 1}."
    if open_ticket:
        offset = NORMAL_OPEN_OFFSETS_HOURS[topic_index * 2 + open_slot]
        when = datetime(2026, 7, 1, 7) + timedelta(hours=offset)
    messages = [
        msg("customer", requester, body, when),
        msg("agent", agent, f"Happy to clarify. {answer} I can also send the relevant setup example for your workspace.", when + timedelta(minutes=24 + variant % 20)),
    ]
    if open_ticket or pending:
        messages.extend([
            msg("customer", requester, PENDING_QUESTIONS[(variant + topic_index) % len(PENDING_QUESTIONS)], when + timedelta(hours=1, minutes=35)),
            msg("agent", agent, PENDING_RESPONSES[(variant + topic_index) % len(PENDING_RESPONSES)], when + timedelta(hours=2, minutes=12)),
        ])
    else:
        messages.append(msg("customer", requester, CONFIRMATIONS[(variant + topic_index) % len(CONFIRMATIONS)], when + timedelta(hours=1, minutes=35)))
    item = envelope(
        index, when, subject, body, category, "low" if variant % 3 else "medium",
        "open" if open_ticket else "pending" if pending else "resolved", tags, messages,
        {"cluster_id": None, "topic_id": topic_id, "is_emerging_trend": False, "root_cause": None, "is_trend_seed": False},
    )
    if open_ticket and topic_index % 2 == 0 and open_slot == 0:
        item["assignee"] = "—"
    return item


def enrich_golden(ticket: dict) -> dict:
    item = deepcopy(ticket)
    cluster_id = item["ground_truth"]["cluster_id"]
    item["ground_truth"]["topic_id"] = cluster_id or {
        "T-20017": "audit_export", "T-20018": "sdk_migration", "T-20019": "audit_retention", "T-20020": "sandbox_cancel"
    }[item["id"]]
    item["ground_truth"]["is_emerging_trend"] = cluster_id is not None
    return item


def validate(tickets: list[dict]) -> None:
    assert len(tickets) == TARGET_TICKET_COUNT
    assert len({ticket["id"] for ticket in tickets}) == TARGET_TICKET_COUNT
    assert len({ticket["subject"] for ticket in tickets}) == TARGET_TICKET_COUNT
    assert len({(ticket["subject"], ticket["body"]) for ticket in tickets}) == TARGET_TICKET_COUNT
    assert sum(ticket["ground_truth"]["is_emerging_trend"] for ticket in tickets) == 96
    assert sum(not ticket["ground_truth"]["is_emerging_trend"] for ticket in tickets) == 1404
    assert Counter(ticket["status"] for ticket in tickets) == {
        "resolved": 1160,
        "pending": 292,
        "open": 48,
    }
    assert all(ticket["messages"] == sorted(ticket["messages"], key=lambda item: item["timestamp"]) for ticket in tickets)
    assert all(ticket["messages"][-1]["author"] == ("customer" if ticket["status"] == "resolved" else "agent") for ticket in tickets)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = [error for ticket in tickets for error in validator.iter_errors(ticket)]
    assert not errors, errors[:3]


def main() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["tickets"]
    tickets = [enrich_golden(ticket) for ticket in golden]
    index = 0
    for cluster_id in TREND_SPECS:
        for variant in range(TREND_VARIANTS_PER_CLUSTER):
            tickets.append(build_trend_ticket(index, cluster_id, variant))
            index += 1
    baseline_total = TARGET_TICKET_COUNT - GOLDEN_TICKET_COUNT - index
    variants_per_topic, extra_variants = divmod(baseline_total, len(BASELINE_TOPICS))
    for topic_index in range(len(BASELINE_TOPICS)):
        variant_count = variants_per_topic + (topic_index < extra_variants)
        for variant in range(variant_count):
            tickets.append(build_baseline_ticket(index, topic_index, variant, variant_count))
            index += 1
    tickets.sort(key=lambda ticket: ticket["created_at"])
    validate(tickets)
    payload = {"dataset": "northstar-cloud-support-v2", "version": "0.3.0", "synthetic": True, "ticket_count": len(tickets), "tickets": tickets}
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(tickets)} synthetic tickets to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
