#!/usr/bin/env python3
"""Reversibly install dataset v2 into the local Trend Detection app."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent.parent
RUNTIME = APP / "data" / "runtime"
DATASET = ROOT / "full_dataset.json"
DB_PATH = RUNTIME / "tickets.db"
ACCOUNTS_PATH = RUNTIME / "accounts.json"
CONVERSATIONS_PATH = RUNTIME / "conversations.json"
CACHE_PATH = RUNTIME / "embeddings_cache.npz"
BACKUPS = RUNTIME / "backups"
MANAGED = (DB_PATH, ACCOUNTS_PATH, CONVERSATIONS_PATH, CACHE_PATH)
EXPECTED_TICKET_COUNT = 1500


def _backup() -> Path:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = BACKUPS / stamp
    destination.mkdir(parents=True)
    manifest = {"created_at": datetime.now().isoformat(), "files": {}}
    for path in MANAGED:
        exists = path.exists()
        manifest["files"][str(path)] = {"exists": exists, "backup_name": path.name}
        if exists:
            shutil.copy2(path, destination / path.name)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return destination


def _requester_email(ticket: dict) -> str:
    slug = ticket["requester"].lower().replace(" ", ".")
    return f"{slug}@northstar-demo.invalid"


def _write_database(tickets: list[dict]) -> None:
    temporary = DB_PATH.with_suffix(".db.importing")
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    connection.execute(
        """CREATE TABLE tickets (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            customer_tier TEXT NOT NULL,
            tags TEXT NOT NULL,
            cluster TEXT,
            requester_email TEXT,
            account_id TEXT,
            requester_name TEXT,
            channel TEXT,
            assignee TEXT
        )"""
    )
    connection.executemany(
        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                ticket["id"], ticket["created_at"], ticket["subject"], ticket["body"],
                ticket["category"], ticket["priority"], ticket["status"], ticket["customer_tier"],
                json.dumps(ticket["tags"]), ticket["ground_truth"]["topic_id"],
                _requester_email(ticket), ticket["account"]["id"], ticket["requester"],
                ticket["channel"].title(), ticket.get("assignee", "Support Team"),
            )
            for ticket in tickets
        ],
    )
    connection.commit()
    assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == EXPECTED_TICKET_COUNT
    connection.close()
    temporary.replace(DB_PATH)


def _write_accounts(tickets: list[dict]) -> None:
    accounts: dict[str, dict] = {}
    for ticket in tickets:
        account = ticket["account"]
        accounts.setdefault(
            account["id"],
            {
                "account_id": account["id"],
                "customer_email": f"billing-{account['id'].lower()}@northstar-demo.invalid",
                "account_name": account["name"],
                "tier": ticket["customer_tier"],
                "arr": account["arr"],
                "region": account["region"],
            },
        )
    payload = {
        "generated_at": "synthetic",
        "source": "data/synthetic/import_to_app.py",
        "description": "Synthetic Northstar Cloud account records",
        "accounts": sorted(accounts.values(), key=lambda item: item["account_id"]),
    }
    ACCOUNTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_conversations(tickets: list[dict]) -> None:
    payload = [{"ticket_id": ticket["id"], "messages": ticket["messages"]} for ticket in tickets]
    CONVERSATIONS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def apply() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    tickets = payload["tickets"]
    if len(tickets) != EXPECTED_TICKET_COUNT or payload.get("synthetic") is not True:
        raise ValueError(f"Expected the validated {EXPECTED_TICKET_COUNT}-ticket synthetic dataset")
    backup = _backup()
    _write_database(tickets)
    _write_accounts(tickets)
    _write_conversations(tickets)
    CACHE_PATH.unlink(missing_ok=True)
    print(f"Installed {len(tickets)} tickets. Backup: {backup}")
    print("Embedding cache removed; rebuild it before starting the app.")


def restore(backup: Path | None) -> None:
    if backup is None:
        candidates = sorted(path for path in BACKUPS.iterdir() if path.is_dir())
        if not candidates:
            raise FileNotFoundError("No dataset-v2 backups found")
        backup = candidates[-1]
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    for raw_path, metadata in manifest["files"].items():
        destination = Path(raw_path)
        if metadata["exists"]:
            shutil.copy2(backup / metadata["backup_name"], destination)
        else:
            destination.unlink(missing_ok=True)
    print(f"Restored app data from {backup}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("apply")
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--backup", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    apply() if args.command == "apply" else restore(args.backup)
