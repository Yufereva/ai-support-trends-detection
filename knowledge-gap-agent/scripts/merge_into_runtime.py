"""Merge Knowledge Gap synthetic tickets into the shared Trend Detection runtime DB.

After this runs, both agents read the same tickets.db:
  - Trend Detection / Zendesk UI at http://localhost:8501
  - Knowledge Gap Agent filters tickets tagged "knowledge-gap"

Usage (from knowledge-gap-agent/):
  python scripts/generate_dataset.py
  python scripts/merge_into_runtime.py

Re-running is safe: previous T-30xxx knowledge-gap rows are replaced.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = ROOT.parent
RUNTIME = APP_ROOT / "data" / "runtime"
DB_PATH = RUNTIME / "tickets.db"
CONVERSATIONS_PATH = RUNTIME / "conversations.json"
ACCOUNTS_PATH = RUNTIME / "accounts.json"
CACHE_PATH = RUNTIME / "embeddings_cache.npz"
KG_TICKETS_PATH = ROOT / "data" / "tickets.json"

KG_TAG = "knowledge-gap"
ID_PREFIX = "T-30"

REQUESTERS = [
    "Jordan Lee",
    "Sam Rivera",
    "Casey Nguyen",
    "Riley Patel",
    "Morgan Blake",
    "Avery Quinn",
    "Cameron Brooks",
    "Jamie Soto",
]


def _load_account_ids() -> list[str]:
    if not ACCOUNTS_PATH.exists():
        return ["A-201"]
    payload = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    return [a["account_id"] for a in payload.get("accounts", [])] or ["A-201"]


def _requester_email(name: str) -> str:
    slug = name.lower().replace(" ", ".")
    return f"{slug}@northstar-demo.invalid"


def _tags_for(ticket: dict) -> list[str]:
    type_tag = "doc-question" if ticket["ticket_type"] in {"question", "how-to"} else "product-bug"
    return [KG_TAG, type_tag, ticket["topic"]]


def _row(ticket: dict, index: int, account_ids: list[str]) -> tuple:
    requester = REQUESTERS[index % len(REQUESTERS)]
    account_id = account_ids[index % len(account_ids)]
    created = ticket["created_at"].replace("Z", "")
    status = "open" if ticket["ticket_type"] in {"question", "how-to"} else "open"
    return (
        ticket["id"],
        created,
        ticket["subject"],
        ticket["body"],
        ticket["product_area"],
        "medium",
        status,
        "pro",
        json.dumps(_tags_for(ticket)),
        ticket["topic"],
        _requester_email(requester),
        account_id,
        requester,
        "Email",
        "Support Team",
    )


def _conversation(ticket: dict, index: int) -> dict:
    requester = REQUESTERS[index % len(REQUESTERS)]
    created = ticket["created_at"].replace("Z", "")
    return {
        "ticket_id": ticket["id"],
        "messages": [
            {
                "author": "customer",
                "name": requester,
                "text": ticket["body"],
                "timestamp": created,
                "type": "public",
            }
        ],
    }


def merge() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Shared DB not found at {DB_PATH}. Run data/synthetic/import_to_app.py apply first."
        )
    tickets = json.loads(KG_TICKETS_PATH.read_text(encoding="utf-8"))
    account_ids = _load_account_ids()

    connection = sqlite3.connect(DB_PATH)
    # Remove any previous knowledge-gap merge (by id prefix or tag).
    existing = connection.execute("SELECT id, tags FROM tickets").fetchall()
    to_delete = []
    for ticket_id, tags_raw in existing:
        if ticket_id.startswith(ID_PREFIX):
            to_delete.append(ticket_id)
            continue
        try:
            tags = json.loads(tags_raw or "[]")
        except json.JSONDecodeError:
            tags = []
        if KG_TAG in tags:
            to_delete.append(ticket_id)
    if to_delete:
        connection.executemany("DELETE FROM tickets WHERE id = ?", [(tid,) for tid in to_delete])

    connection.executemany(
        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [_row(ticket, index, account_ids) for index, ticket in enumerate(tickets)],
    )
    connection.commit()
    total = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    connection.close()

    conversations = []
    if CONVERSATIONS_PATH.exists():
        conversations = json.loads(CONVERSATIONS_PATH.read_text(encoding="utf-8"))
    conversations = [
        item
        for item in conversations
        if not str(item.get("ticket_id", "")).startswith(ID_PREFIX)
    ]
    conversations.extend(_conversation(ticket, index) for index, ticket in enumerate(tickets))
    CONVERSATIONS_PATH.write_text(json.dumps(conversations, indent=2) + "\n", encoding="utf-8")

    # Trend Detection embeddings include every ticket id; force rebuild.
    CACHE_PATH.unlink(missing_ok=True)
    kg_cache = ROOT / "data" / "embeddings_cache.npz"
    kg_cache.unlink(missing_ok=True)

    print(f"Merged {len(tickets)} Knowledge Gap tickets into {DB_PATH}")
    print(f"Shared DB now has {total} tickets. Embedding caches cleared.")
    print("Open evidence tickets in Zendesk: http://localhost:8501/?ticket=T-30001&mode=detail")


if __name__ == "__main__":
    merge()
