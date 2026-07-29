# Limitations

- The committed dataset and all account-impact values are synthetic.
- Evaluation uses seeded labels and is not evidence of production accuracy.
- The English embedding model has not been evaluated for multilingual support.
- Category matching depends on upstream category labels being present and correct.
- A fixed 0.60 similarity threshold and seven-day window require calibration for real ticket volume.
- Similar wording can still produce false positives; different wording can hide a real trend.
- The application does not infer or prove root cause.
- Zendesk, Jira, and Salesforce behavior is simulated locally; no authenticated production integrations exist.
- Runtime authentication, authorization, encryption, audit logging, retention, and monitoring are not implemented.
- Suggested ARR impact and engineering priority are review aids, not automated decisions.
