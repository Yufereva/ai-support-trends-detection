"""Rule-based escalation draft quality scoring.

Operational question: Is this support→engineering escalation draft
complete enough to hand to Engineering?

Scores a structured draft (same shape as Trend Detection's
``generate_engineering_ticket`` output, plus optional richer fields used
by the synthetic demo set). Never blocks creation — it surfaces gaps for
a human reviewer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DRAFTS_PATH = DATA_DIR / "drafts.json"

# Transparent review thresholds (not model certainty).
MIN_SUMMARY_CHARS = 80
MIN_EVIDENCE_TICKETS = 3
PASS_SCORE = 0.75
NEEDS_WORK_SCORE = 0.50

EXPECTED_ACTUAL_RE = re.compile(
    r"\b(expected|actual|observed)\b.{0,80}\b(expected|actual|observed)\b"
    r"|\bexpected\s*(behavior|result|outcome)\b"
    r"|\bactual\s*(behavior|result|outcome)\b",
    re.IGNORECASE | re.DOTALL,
)
REPRO_OR_ENV_RE = re.compile(
    r"\b(repro(duce|duction)?|steps?\s+to\s+reproduce|environment|version|"
    r"build|region|tenant|staging|production)\b",
    re.IGNORECASE,
)
EXPLICIT_GAP_RE = re.compile(
    r"\b(missing|not\s+yet|unknown|to\s+be\s+collected|needs?\s+follow[- ]?up)\b"
    r".{0,40}\b(repro|environment|version|steps)\b",
    re.IGNORECASE | re.DOTALL,
)

VERDICT_RANK = {"poor": 0, "needs_work": 1, "ready": 2}


def load_drafts() -> list[dict]:
    return json.loads(DRAFTS_PATH.read_text(encoding="utf-8"))


def _text_blob(draft: dict) -> str:
    parts = [
        str(draft.get("title") or ""),
        str(draft.get("summary") or ""),
        str(draft.get("description") or ""),
        str(draft.get("expected_behavior") or ""),
        str(draft.get("actual_behavior") or ""),
        str(draft.get("reproduction_steps") or ""),
        str(draft.get("environment") or ""),
    ]
    return "\n".join(parts)


def _evidence_ids(draft: dict) -> list[str]:
    ids = list(draft.get("similar_ticket_ids") or [])
    trigger = draft.get("trigger_ticket_id")
    if trigger and trigger not in ids:
        ids = [trigger, *ids]
    return [str(item) for item in ids if item]


def _impact(draft: dict) -> dict:
    return dict(draft.get("customer_impact") or {})


def _check_title(draft: dict) -> tuple[bool, str]:
    title = (draft.get("title") or "").strip()
    if len(title) < 12:
        return False, "Title is missing or too short for Engineering triage."
    if title.lower() in {"trend", "issue", "bug", "escalation"}:
        return False, "Title is too generic."
    return True, "Title is present and specific enough to scan."


def _check_summary(draft: dict) -> tuple[bool, str]:
    summary = (draft.get("summary") or draft.get("description") or "").strip()
    if len(summary) < MIN_SUMMARY_CHARS:
        return (
            False,
            f"Summary is under {MIN_SUMMARY_CHARS} characters — Engineering lacks context.",
        )
    return True, "Summary has enough narrative context."


def _check_trigger(draft: dict) -> tuple[bool, str]:
    if draft.get("trigger_ticket_id"):
        return True, f"Trigger ticket {draft['trigger_ticket_id']} is linked."
    return False, "No trigger support ticket is linked."


def _check_evidence(draft: dict) -> tuple[bool, str]:
    ids = _evidence_ids(draft)
    similar_only = [i for i in ids if i != draft.get("trigger_ticket_id")]
    count = draft.get("similar_count")
    if count is None:
        count = len(similar_only)
    if count < MIN_EVIDENCE_TICKETS and len(similar_only) < MIN_EVIDENCE_TICKETS:
        return (
            False,
            f"Fewer than {MIN_EVIDENCE_TICKETS} evidence tickets — weak pattern signal.",
        )
    return True, f"{max(count, len(similar_only))} evidence tickets linked."


def _check_impact(draft: dict) -> tuple[bool, str]:
    impact = _impact(draft)
    accounts = int(impact.get("unique_accounts") or 0)
    arr = str(impact.get("arr_at_risk_formatted") or draft.get("arr_at_risk") or "").strip()
    has_arr = bool(arr) and arr not in {"$0", "$0K", "0", "—", "-"}
    if accounts <= 0 and not has_arr:
        return False, "No customer impact (accounts or ARR) is stated."
    bits = []
    if accounts:
        bits.append(f"{accounts} accounts")
    if has_arr:
        bits.append(f"ARR {arr}")
    return True, "Customer impact noted: " + ", ".join(bits) + "."


def _check_expected_vs_actual(draft: dict) -> tuple[bool, str]:
    expected = (draft.get("expected_behavior") or "").strip()
    actual = (draft.get("actual_behavior") or "").strip()
    if expected and actual:
        return True, "Expected vs actual behavior are both present."
    blob = _text_blob(draft)
    if EXPECTED_ACTUAL_RE.search(blob):
        return True, "Expected vs actual behavior is described in the draft text."
    return False, "Expected vs actual behavior is missing."


def _check_repro_or_env(draft: dict) -> tuple[bool, str]:
    if (draft.get("reproduction_steps") or "").strip():
        return True, "Reproduction steps are present."
    if (draft.get("environment") or "").strip():
        return True, "Environment / version context is present."
    blob = _text_blob(draft)
    if REPRO_OR_ENV_RE.search(blob):
        return True, "Reproduction or environment details appear in the draft."
    if EXPLICIT_GAP_RE.search(blob):
        return True, "Draft explicitly notes missing repro/environment as a follow-up."
    return False, "No reproduction steps, environment, or explicit evidence gap note."


def _check_priority(draft: dict) -> tuple[bool, str]:
    priority = (draft.get("priority") or "").strip().lower()
    if priority in {"low", "medium", "high", "urgent"}:
        return True, f"Priority is set ({priority})."
    return False, "Priority is missing or not in Low/Medium/High/Urgent."


# (id, label, weight, required_for_ready, checker)
CHECK_SPECS: list[tuple[str, str, float, bool, Callable[[dict], tuple[bool, str]]]] = [
    ("title", "Clear title", 0.10, True, _check_title),
    ("summary", "Substantive summary", 0.15, True, _check_summary),
    ("trigger", "Trigger ticket linked", 0.10, True, _check_trigger),
    ("evidence", "Evidence tickets", 0.20, True, _check_evidence),
    ("impact", "Customer impact", 0.15, True, _check_impact),
    # Required for "ready": Engineering needs behavior contrast + repro/env
    # (or an explicit gap note). Live Trend drafts usually miss these → needs_work.
    ("expected_vs_actual", "Expected vs actual", 0.15, True, _check_expected_vs_actual),
    ("repro_or_environment", "Repro / environment", 0.10, True, _check_repro_or_env),
    ("priority", "Priority set", 0.05, True, _check_priority),
]


def _verdict(score: float, checks: list[dict]) -> str:
    required_failed = [c for c in checks if c["required_for_ready"] and not c["passed"]]
    if score >= PASS_SCORE and not required_failed:
        return "ready"
    if score >= NEEDS_WORK_SCORE:
        return "needs_work"
    return "poor"


def score_draft(draft: dict) -> dict:
    """Score one escalation draft and return a reviewable quality report."""
    checks: list[dict] = []
    earned = 0.0
    total = 0.0
    for check_id, label, weight, required, checker in CHECK_SPECS:
        passed, detail = checker(draft)
        checks.append(
            {
                "id": check_id,
                "label": label,
                "weight": weight,
                "required_for_ready": required,
                "passed": passed,
                "detail": detail,
            }
        )
        total += weight
        if passed:
            earned += weight

    score = round(earned / total, 3) if total else 0.0
    verdict = _verdict(score, checks)
    gaps = [c for c in checks if not c["passed"]]
    return {
        "draft_id": draft.get("id"),
        "title": draft.get("title"),
        "score": score,
        "score_pct": int(round(score * 100)),
        "verdict": verdict,
        "checks": checks,
        "gaps": gaps,
        "passed_count": sum(1 for c in checks if c["passed"]),
        "check_count": len(checks),
        "recommendation": recommendation_for(verdict, gaps),
    }


def recommendation_for(verdict: str, gaps: list[dict]) -> str:
    if verdict == "ready":
        return (
            "Draft looks complete enough for Engineering review. "
            "A human should still confirm priority and impact."
        )
    gap_labels = ", ".join(g["label"] for g in gaps) or "listed gaps"
    if verdict == "needs_work":
        return (
            f"Strengthen before escalating, or proceed with an explicit caveat. "
            f"Missing: {gap_labels}."
        )
    return (
        f"Draft is too thin for a useful Engineering handoff. "
        f"Add: {gap_labels}."
    )


def score_all_drafts(drafts: list[dict] | None = None) -> list[dict]:
    items = drafts if drafts is not None else load_drafts()
    reports = [score_draft(d) for d in items]
    reports.sort(
        key=lambda r: (VERDICT_RANK[r["verdict"]], r["score"], r.get("draft_id") or ""),
        reverse=True,
    )
    return reports


def format_quality_summary(report: dict) -> str:
    gaps = "; ".join(g["label"] for g in report["gaps"]) or "none"
    return (
        f"Escalation quality: {report['verdict']} "
        f"({report['score_pct']}%, {report['passed_count']}/{report['check_count']} checks). "
        f"Gaps: {gaps}."
    )


VERDICT_LABELS = {
    "ready": "Ready for Engineering",
    "needs_work": "Needs work before handoff",
    "poor": "Poor — too thin to escalate",
}

VERDICT_COLORS = {
    "ready": "#2f9e44",
    "needs_work": "#f59f00",
    "poor": "#e35b5b",
}


def quality_panel_html(report: dict, *, compact: bool = False) -> str:
    """HTML snippet for Trend Detection / Jira soft-gate panels.

    Full mode lists all checklist items with pass/gap state. Compact mode
    keeps a short-form summary suitable for the Zendesk sidebar.
    """
    import html as html_lib

    color = VERDICT_COLORS[report["verdict"]]
    label = VERDICT_LABELS[report["verdict"]]
    checks = report.get("checks") or []
    gaps = report["gaps"]

    if compact:
        checks_html = ""
        if gaps:
            checks_html = (
                "<div style='margin-top:6px;font-size:12px;color:#6b7280;'>"
                "Gaps: "
                + html_lib.escape(", ".join(g["label"] for g in gaps))
                + "</div>"
            )
        elif checks:
            checks_html = (
                "<div style='margin-top:6px;font-size:12px;color:#6b7280;'>"
                f"{report['passed_count']}/{report['check_count']} checks passed."
                "</div>"
            )
    else:
        rows = []
        for check in checks:
            passed = bool(check.get("passed"))
            mark = "Pass" if passed else "Gap"
            mark_color = "#2f9e44" if passed else "#e35b5b"
            rows.append(
                "<div style='display:flex;gap:8px;align-items:flex-start;"
                "margin:0;padding:3px 0;font-size:12px;line-height:1.35;'>"
                f"<span style='flex:0 0 36px;font-weight:700;color:{mark_color};'>"
                f"{mark}</span>"
                "<span style='min-width:0;'>"
                f"<span style='font-weight:600;color:#172B4D;'>"
                f"{html_lib.escape(check['label'])}</span>"
                f"<span style='color:#6b7280;'> — "
                f"{html_lib.escape(check['detail'])}</span>"
                "</span></div>"
            )
        checks_html = (
            "<div style='margin-top:8px;padding-top:6px;"
            "border-top:1px solid #e5e7eb;'>"
            + "".join(rows)
            + "</div>"
        )

    caveat = ""
    if report["verdict"] != "ready":
        caveat = (
            "<div style='margin-top:8px;font-size:12px;color:#6b7280;'>"
            "Soft gate: you can still create the Jira issue — enrich the draft "
            "or proceed with this caveat visible to reviewers."
            "</div>"
        )
    return (
        f"<div class='eq-quality-panel' style='border-left:4px solid {color};"
        f"padding:10px 12px;background:#f8fafc;border-radius:6px;"
        f"margin:12px 0 4px;box-sizing:border-box;'>"
        f"<div style='font-weight:700;color:{color};'>"
        f"Escalation Quality · {html_lib.escape(label)} "
        f"({report['score_pct']}%)</div>"
        f"<div style='margin-top:4px;font-size:13px;'>"
        f"{html_lib.escape(report['recommendation'])}</div>"
        f"{checks_html}{caveat}</div>"
    )
