# Synthetic Demo Dataset

`sample_tickets.csv` contains fictional support tickets created for this portfolio repository.

No real customer, employer, account, email, or private URL data is included. The data is designed only to demonstrate trend detection behavior and should not be treated as production data.

## Included Patterns

The dataset intentionally includes recurring support themes:

- CSV export failures or timeouts
- SSO login failures
- API rate-limit confusion
- Billing invoice requests
- Search performance degradation
- Permissions confusion
- Slack integration disconnects
- Feature requests for bulk actions
- Unrelated background tickets

At least two themes increase in the most recent analysis period so the app can demonstrate period-over-period growth. Some tickets use the `enterprise` tier to support customer-impact framing.

## Schema

| Column | Description |
|---|---|
| `ticket_id` | Synthetic ticket identifier |
| `created_at` | Ticket creation date |
| `subject` | Short synthetic ticket subject |
| `description` | Synthetic ticket description |
| `product_area` | Product or workflow area |
| `customer_tier` | `free`, `pro`, or `enterprise` |
| `priority` | Synthetic support priority |
| `status` | Synthetic ticket status |
| `channel` | Synthetic support channel |
| `tags` | Pipe-separated theme tags |

## Evaluation Use

This dataset supports local testing of ingestion, privacy redaction, duplicate handling, clustering, trend scoring, and report generation. It is intentionally small enough for fast local review.
