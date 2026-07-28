# Product Requirements

## Problem

Support teams often see a product problem across several customer conversations before it reaches Product or Engineering. Manual discovery is slow, and an escalation can lack consistent evidence or business-impact context.

## Users

- Support agents handling incoming tickets
- Support Operations and Support Engineering reviewers
- Product and Engineering partners reviewing escalations

## MVP Goals

- Check every incoming ticket for a possible emerging trend.
- Keep ordinary tickets free of unnecessary warnings.
- Show the evidence and rules behind every warning.
- Connect related tickets to synthetic customer-impact context.
- Prepare a reviewable engineering-ticket draft.
- Remain reproducible without paid APIs or customer data.

## Functional Requirements

- Import the committed 1,500-ticket synthetic dataset into local runtime storage.
- Create and cache normalized sentence-transformer embeddings.
- Compare an incoming ticket with the previous seven days of same-category history.
- Trigger a warning at three or more matches with similarity at or above 0.60.
- Display top matches, scores, ticket links, timeline, and impact.
- Support known ticket IDs and free-text API analysis.
- Create and browse local Jira-style drafts after an explicit action.
- Return a structured warning from the incoming-ticket webhook.

## Non-Functional Requirements

- Run locally on Python 3.11 or newer.
- Require no secret or paid model provider.
- Keep generated databases and embeddings out of Git.
- Preserve visible thresholds and supporting ticket IDs.
- Pass automated tests and Ruff in GitHub Actions.

## Non-Goals

- Live Zendesk, Atlassian, Salesforce, or Slack access.
- Autonomous incident declaration or customer messaging.
- Automated root-cause analysis.
- Production authentication, authorization, or data governance.
- Replacing Support, Product, or Engineering judgment.

## Success Criteria

- Seeded true-trend tickets receive warnings.
- Seeded ordinary tickets do not receive warnings.
- Boundary outcomes are explainable from category, time, count, and similarity scores.
- The complete queue-to-Jira-draft demo works from a clean local setup.
- Regression tests protect the incoming-ticket workflow and stale local Jira references.
