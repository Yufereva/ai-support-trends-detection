# AI Support Trend Detection

[![tests](https://github.com/Yufereva/ai-support-trends-detection/actions/workflows/tests.yml/badge.svg)](https://github.com/Yufereva/ai-support-trends-detection/actions/workflows/tests.yml)

AI-assisted workflow for detecting emerging support trends, recurring customer friction, and product issues from support tickets.

**Project status:** Portfolio MVP

> All sample data in this repository is synthetic. No customer or former employer data is included.

## Screenshot

![AI Support Trend Detection dashboard](assets/app-screenshot.png)

## Why This Exists

Support teams often discover customer pain before Product and Engineering because they see recurring friction directly in ticket queues. Those signals can remain fragmented across individual conversations, making it difficult to distinguish an emerging product issue from isolated support requests.

AI Support Trend Detection surfaces those patterns earlier and turns them into evidence-based recommendations for Support Operations, Product, and Engineering. It is designed to strengthen human decision-making, not replace it: a responsible reviewer validates every trend before it becomes an escalation or operational action.

## Business Problem

Support teams often see product friction before other teams do, but the signal is distributed across many individual tickets. Important patterns can remain anecdotal until a support leader manually reviews ticket queues, searches for similar cases, and assembles evidence for Product or Engineering.

This portfolio application is designed to help Support Operations identify emerging customer friction earlier and produce reviewable, evidence-backed trend summaries.

## What The System Does

- Loads a synthetic support ticket dataset or reviewer-uploaded CSV.
- Validates the required ticket schema.
- Redacts obvious PII-like strings before analysis.
- Combines ticket subject, description, product area, and tags.
- Uses a transparent TF-IDF and clustering baseline to group related tickets.
- Compares current and previous periods to identify growth.
- Ranks detected trends by volume, growth, customer tier, and priority.
- Produces supporting ticket IDs, impact framing, and recommended next action.

## Intended Users

- Support Operations leaders
- Support Managers
- Support Engineering teams
- Product Operations partners
- Product and Engineering leaders reviewing customer friction

## Current Capabilities

- Detects emerging ticket clusters
- Measures trend growth over time
- Produces evidence-backed Product reports
- Supports reviewer-uploaded ticket datasets
- Exports findings as Markdown and JSON

## Example Detected Trend

The included synthetic dataset produces a trend similar to:

```text
Trend: CSV exports timing out for large datasets
Classification: Emerging product issue
Evidence: 55 current-period tickets vs 23 prior-period tickets
Customer impact: recurring reporting/export friction, including enterprise-tier tickets
Recommended action: open a Product/Engineering investigation after human review
Suggested priority: P1
Confidence: High
```

These values are generated from synthetic data and should not be interpreted as production measurements.

## How The System Works

```mermaid
flowchart LR
    A[Support Tickets] --> B[Data Validation]
    B --> C[PII Redaction]
    C --> D[Similarity Detection]
    D --> E[Trend Detection]
    E --> F[Evidence Collection]
    F --> G[Product Report]
    G --> H[Human Review]
```

Implementation details, including the current TF-IDF and clustering baseline, are documented in [Architecture](docs/architecture.md).

## Business Value

The MVP is intended to support:

- earlier visibility into emerging customer friction;
- reduced manual ticket review;
- better evidence quality for Product and Engineering;
- clearer linkage between individual tickets and broader customer-impact patterns;
- human-reviewable recommendations rather than automated operational decisions.

## Intended Success Metrics

For a future pilot, this workflow could be evaluated using:

- time to identify a review-worthy trend;
- trend precision and recall against known escalations;
- reviewer acceptance rate;
- evidence coverage per escalation;
- manual analysis time saved;
- false-positive rate.

## Privacy And Responsible AI

All committed data is synthetic. The MVP does not require API keys or access to customer systems.

The system is designed for human review. It should not automatically declare incidents, create customer-facing messages, or assign engineering priority without a responsible reviewer.

See [Privacy and Responsible AI](docs/privacy-and-responsible-ai.md).

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

The app loads `data/sample_tickets.csv` by default. You can also upload a CSV with the same schema from the sidebar.

### Test And Lint

```bash
pytest
ruff check .
```

## Input Schema

Required CSV columns:

| Column | Description |
|---|---|
| `ticket_id` | Synthetic or source ticket identifier |
| `created_at` | Ticket creation date |
| `subject` | Ticket subject |
| `description` | Ticket body or summary |
| `product_area` | Product or workflow area |
| `customer_tier` | Customer segment or tier |
| `priority` | Ticket priority |
| `status` | Ticket status |
| `channel` | Support channel |
| `tags` | Pipe-separated tags |

## Repository Structure

```text
app.py                         Streamlit review interface
src/support_trend_detection/   Testable trend detection logic
data/                          Synthetic sample dataset
examples/                      Generated example outputs
docs/                          Architecture, privacy, rollout, evaluation
tests/                         Core pytest suite
.github/                       CI, issue templates, PR template
```

## Documentation

- [Architecture](docs/architecture.md)
- [Product Requirements](docs/product-requirements.md)
- [Product Workflow](docs/product-workflow.md)
- [Future Agent Portfolio](docs/future-agents.md)
- [Privacy and Responsible AI](docs/privacy-and-responsible-ai.md)
- [Evaluation Framework](docs/evaluation-framework.md)
- [Rollout Plan](docs/rollout-plan.md)
- [Limitations](docs/limitations.md)

## Current Limitations

- Synthetic data only.
- Baseline clustering, not production ML.
- No live Zendesk, Jira, Slack, or CRM integrations.
- No multilingual evaluation.
- No production security review.
- No causal inference.
- False positives and false negatives are possible.

## Roadmap

- [x] Synthetic support ticket dataset
- [x] Local trend detection pipeline
- [x] Streamlit review interface
- [x] Evidence-backed trend output
- [x] Core test coverage
- [x] GitHub Actions quality checks
- [ ] LLM-assisted summaries
- [ ] Zendesk ingestion
- [ ] Jira export
- [ ] Slack notifications
- [ ] Scheduled trend monitoring
- [ ] Human approval workflow

## Future AI Agents

This repository is the first module of a broader AI Support Operations Platform. Each planned agent will become its own portfolio project focused on a distinct operational problem:

- **Trend Detection Agent (current):** identifies emerging customer friction and prepares evidence for Product and Engineering review.
- **Knowledge Gap Agent:** finds recurring questions that indicate missing or ineffective help content.
- **Repro Agent:** converts support evidence into structured, reviewable reproduction steps.
- **Log Analysis Agent:** helps Support Engineering identify relevant errors and diagnostic signals.
- **Incident Copilot:** supports incident coordination, evidence gathering, and stakeholder updates with human oversight.

## Related Portfolio Projects

This repository is part of a portfolio of AI-assisted workflows designed around real Support Operations and Support Engineering problems.

Additional standalone agent repositories will be linked here as they are released.

## License

MIT License. See [LICENSE](LICENSE).
