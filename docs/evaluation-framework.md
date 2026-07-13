# Evaluation Framework

This framework separates what can be evaluated with the synthetic dataset from what requires a real operational pilot.

## Metrics Testable With Synthetic Data

| Metric | How to evaluate |
|---|---|
| Cluster coherence | Review whether top tickets in a detected trend share the same theme |
| Trend precision | Measure how many detected synthetic trends match intentionally seeded themes |
| False-positive rate | Count detected trends that map to unrelated background tickets |
| Evidence coverage | Verify each trend includes supporting ticket IDs and product areas |
| Determinism | Re-run the pipeline and compare output order and scores |
| Stability | Change the window slightly and inspect whether major trends remain visible |

## Metrics Requiring An Operational Pilot

| Metric | Why synthetic data is insufficient |
|---|---|
| Trend recall | Requires known real-world issue labels |
| Time-to-detection | Requires historical operational timelines |
| Reviewer acceptance rate | Requires support leader review |
| Manual analysis time saved | Requires comparison with existing team workflow |
| Escalation quality | Requires Product and Engineering feedback |

## Suggested Review Process

1. Run the pipeline on a labeled historical ticket export.
2. Have support leaders review detected trends.
3. Compare detected themes with known escalations or incidents.
4. Track accepted, rejected, and missed trends.
5. Tune thresholds and confidence explanations.
6. Re-run evaluation before any operational rollout.
