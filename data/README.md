# Data

## Published Synthetic Data

`synthetic/full_dataset.json` contains 1,500 fictional support tickets, conversations, accounts, and known evaluation labels. The generator creates recurring incidents, ordinary support questions, and boundary cases without copying customer data.

Supporting files include:

- `ticket-schema-v2.json`: JSON Schema for a ticket record;
- `generate_full_dataset.py`: deterministic full-dataset generator;
- `golden_sample.json`: smaller reviewed examples;
- `golden_sample_review.md`: human-readable conversation review;
- `evaluate_full_dataset.py`: labeled trend-detection evaluation;
- `import_to_app.py`: reversible conversion into local runtime files.

## Generated Runtime Data

Run:

```bash
python data/synthetic/import_to_app.py apply
```

This creates `data/runtime/tickets.db`, `accounts.json`, and `conversations.json`. Trend analysis later creates `embeddings_cache.npz`, while local Jira actions may create `jira_issues.json`. The entire runtime directory is ignored because it contains generated demo state.

To restore the most recent local state saved by the importer:

```bash
python data/synthetic/import_to_app.py restore
```

All names, emails, companies, request IDs, account values, and URLs use fictional demo values.
