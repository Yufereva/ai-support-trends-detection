"""Customer business impact from similar ticket clusters (Salesforce ARR)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME_PATH = ROOT / "data" / "runtime"
DB_PATH = RUNTIME_PATH / "tickets.db"
ACCOUNTS_PATH = RUNTIME_PATH / "accounts.json"


def load_accounts() -> dict[str, dict]:
    if not ACCOUNTS_PATH.exists():
        return {}
    data = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    return {a["account_id"]: a for a in data.get("accounts", [])}


def _ticket_account_lookup() -> dict[str, str]:
    """Map ticket_id -> account_id from tickets.db."""
    conn = sqlite3.connect(DB_PATH)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    if "account_id" not in columns:
        conn.close()
        return {}

    rows = conn.execute(
        "SELECT id, account_id FROM tickets WHERE account_id IS NOT NULL"
    ).fetchall()
    conn.close()
    return {ticket_id: account_id for ticket_id, account_id in rows}


def format_arr(amount: int) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${round(amount / 1_000)}K"
    return f"${amount:,}"


def calculate_customer_impact(
    similar_ticket_ids: list[str],
    trigger_ticket_id: str | None = None,
) -> dict:
    accounts = load_accounts()
    ticket_accounts = _ticket_account_lookup()

    ticket_ids = list(similar_ticket_ids)
    if trigger_ticket_id and trigger_ticket_id not in ticket_ids:
        ticket_ids.append(trigger_ticket_id)

    seen_accounts: dict[str, dict] = {}
    for ticket_id in ticket_ids:
        account_id = ticket_accounts.get(ticket_id)
        if not account_id or account_id in seen_accounts:
            continue
        account = accounts.get(account_id)
        if account:
            seen_accounts[account_id] = account

    by_tier = {"enterprise": 0, "pro": 0, "free": 0}
    arr_by_tier = {"enterprise": 0, "pro": 0, "free": 0}
    for account in seen_accounts.values():
        tier = account.get("tier", "free")
        if tier not in by_tier:
            tier = "free"
        by_tier[tier] += 1
        arr_by_tier[tier] += account.get("arr", 0)

    top_accounts = sorted(
        seen_accounts.values(),
        key=lambda a: a.get("arr", 0),
        reverse=True,
    )[:5]

    arr_at_risk = sum(a.get("arr", 0) for a in seen_accounts.values())

    return {
        "total_tickets": len(ticket_ids),
        "unique_accounts": len(seen_accounts),
        "by_tier": by_tier,
        "arr_by_tier": arr_by_tier,
        "arr_at_risk": arr_at_risk,
        "arr_at_risk_formatted": format_arr(arr_at_risk),
        "top_accounts": [
            {
                "name": a["account_name"],
                "arr": a["arr"],
                "tier": a["tier"],
                "arr_formatted": format_arr(a["arr"]),
            }
            for a in top_accounts
        ],
    }
