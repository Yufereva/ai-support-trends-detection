# Limitations & Human-in-the-Loop Boundary

## What this prototype does

- Scores a support→engineering escalation draft with an explicit, weighted
  checklist (title, summary, trigger, evidence, impact, expected vs actual,
  repro/environment, priority).
- Returns a transparent verdict: **ready**, **needs_work**, or **poor**, plus
  the exact checks that passed or failed.
- Surfaces the same score inside Trend Detection before Create in Jira as a
  soft gate — a warning, not an automatic block.
- Gives the Jira Create form dedicated Expected behavior, Actual behavior,
  Reproduction steps, and Environment / version fields. **Re-check escalation
  quality** rescores from those fields, and their content is written into the
  created issue description.

## What this prototype does not do

- It does not create, edit, or delete Jira issues on its own.
- It does not judge whether the underlying product issue is real — only whether
  the escalation package is complete enough for Engineering to start.
- It does not use an LLM. Keyword/structure rules can miss well-written prose
  that avoids the expected phrases, or pass drafts that mention "expected"
  without being useful.
- Thresholds (`PASS_SCORE`, `NEEDS_WORK_SCORE`, `MIN_EVIDENCE_TICKETS`) were
  chosen for this synthetic demo set and the live Trend Detection draft shape.
  They are not calibrated on real escalations.
- Live Trend Detection drafts start at **needs_work** because they include
  evidence and impact but omit expected/actual and repro — that is intentional
  demo behavior, not a model failure. Filling the four enrichment fields in the
  Create form moves the same draft to **ready**.
- Scoring is wired only to escalations that originate from a Trend Detection
  draft. A Jira issue created outside that flow is not scored — extending the
  soft gate to plain Jira tickets is out of scope for this MVP.

## Human-in-the-loop

Every score lists the failed checks. The reviewer may enrich the draft, note
an explicit evidence gap, or proceed to Create in Jira with the caveat visible.
The agent never assumes the recommendation is correct and never blocks
escalation without a human decision.
