# Support Dataset v2

This folder is the published source for the application's synthetic runtime data.
`import_to_app.py` converts it into the ignored local database and JSON files.

## Fictional product

**Northstar Cloud** is a fictional B2B SaaS developer platform with REST APIs,
webhooks, data exports, billing, SSO, SCIM, and audit logs.

## Golden sample

`golden_sample.json` contains 20 fully synthetic tickets:

- 4 API authentication tickets caused by a stale production gateway cache.
- 4 webhook delay tickets caused by a regional delivery-worker backlog.
- 4 billing tickets caused by a duplicated proration job.
- 4 SSO/SCIM tickets caused by stale group-membership cache entries.
- 4 unrelated tickets that should not be grouped into those trends.

Every conversation is tied to its ticket's symptoms, investigation, and outcome.
Names, companies, identifiers, and business data are fictional.

## Quality rules

1. Agent replies must reference concrete details from the preceding customer message.
2. A resolution must name the action taken; generic "this is fixed" replies are not allowed.
3. Support gathers evidence and communicates status; specialist teams perform backend changes.
4. Technical findings and remediation are recorded as internal specialist notes.
5. A resolved ticket ends with customer confirmation; a pending ticket ends with a clear next step.
6. Tickets in one ground-truth cluster share a root cause but use different wording.
7. Unrelated tickets must remain semantically distinct from trend clusters.
8. No real customer information, credentials, URLs, or company-confidential data.
9. Ground-truth fields are evaluation labels and are not shown to the detection model.

## Files

| File | Purpose |
|---|---|
| `ticket-schema-v2.json` | Schema for tickets, messages, and evaluation labels |
| `generate_golden_sample.py` | Deterministic, curated sample generator |
| `golden_sample.json` | Generated 20-ticket review artifact |
| `golden_sample_review.md` | Human-readable review of every conversation |
| `evaluate_golden_sample.py` | Embedding quality and threshold calibration |
| `generate_full_dataset.py` | Deterministic 1,500-ticket dataset generator |
| `full_dataset.json` | Generated full synthetic dataset |
| `evaluate_full_dataset.py` | Semantic retrieval and time-window alert calibration |

## Generate and validate

```bash
python data/synthetic/generate_golden_sample.py
python data/synthetic/evaluate_golden_sample.py
python data/synthetic/generate_full_dataset.py
python data/synthetic/evaluate_full_dataset.py
```

The script validates IDs, required fields, message ordering, status endings, and the
expected 4 x 4 trend seeds plus 4 unrelated tickets before writing JSON.

## Full dataset

The approved Golden Sample has been scaled to 1,500 tickets:

- 96 tickets in four emerging-trend bursts, including the 16 trend seeds;
- 1,404 normal support tickets across 16 recurring topics;
- 1,160 resolved, 292 pending, and 48 open tickets;
- 5,064 chronological public and internal messages;
- 1,500 unique subjects and subject/body pairs.

Recurring baseline topics are spread across two years. Emerging trends are
concentrated into five days. Evaluation labels distinguish semantic topic from
time-based emerging-trend status; neither field is exposed to the detection model.

With `all-MiniLM-L6-v2`, nearest-neighbor topic accuracy is 99.8% on this deterministic
synthetic benchmark. A rule requiring three earlier same-category tickets in seven days
at cosine `0.60` gives 100.0% precision, 92.9% recall, and 96.3% F1. The existing `0.75`
cutoff reaches only 54.8% recall. These figures are a local synthetic baseline, not a
claim about production performance, and must be rechecked after application import.
