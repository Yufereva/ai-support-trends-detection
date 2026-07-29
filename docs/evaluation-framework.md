# Evaluation Framework

## Synthetic Evaluation

`data/synthetic/full_dataset.json` contains explicit ground-truth labels for seeded trends and ordinary support cases. Run:

```bash
python data/synthetic/evaluate_full_dataset.py
```

The evaluation reports precision, recall, F1, false positives, and false negatives for the fixed incoming-ticket rule. Golden-sample files support manual conversation and semantic-coherence review.

## Regression Coverage

Automated tests cover:

- trend and non-trend batch decisions;
- the same-category false-positive guard;
- automatic warning payloads from the incoming webhook;
- similar-ticket evidence in Jira drafts;
- graceful handling of stale ticket references in the local Jira backlog.

## Production Evaluation Needed

Synthetic results cannot establish production accuracy. A real pilot would need approved historical data and measure:

- recall against known escalations;
- reviewer acceptance, revision, and rejection rates;
- time to detect a review-worthy issue;
- false-positive burden on support agents;
- evidence quality rated by Product and Engineering;
- performance across languages, products, and changing ticket volume.

Thresholds should be calibrated in shadow mode before any operational action is enabled.
