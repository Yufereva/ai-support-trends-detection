# Limitations

- The committed dataset is synthetic and intentionally simplified.
- The current system uses baseline TF-IDF and KMeans clustering, not a production ML platform.
- No live Zendesk, Jira, Slack, or CRM integrations are implemented.
- No multilingual evaluation has been performed.
- No production security review has been performed.
- The system does not prove causality.
- False positives are possible when unrelated tickets share similar wording.
- False negatives are possible when emerging issues use inconsistent language.
- Cluster drift may occur as ticket language changes over time.
- Evaluation coverage is limited to synthetic data and local tests.
- Suggested priorities are review aids, not operational decisions.
