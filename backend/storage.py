"""SQLite persistence for processed invoice records."""

import json
import os
from pathlib import Path
import sqlite3
from typing import Any


DATABASE_PATH = Path(
    os.environ.get(
        "TRUESCOPE_DATABASE_PATH",
        Path(__file__).resolve().parent.parent
        / "database"
        / "truescope.sqlite3",
    )
)


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT,
                error_json TEXT,
                source_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_invoice(invoice_id: str, record: dict[str, Any]) -> None:
    initialize_database()
    result_json = json.dumps(record.get("result"), allow_nan=False)
    error_json = json.dumps(record.get("error"), allow_nan=False)
    source_json = json.dumps(record.get("source", {}), allow_nan=False)

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO invoices (
                invoice_id, status, result_json, error_json, source_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(invoice_id) DO UPDATE SET
                status = excluded.status,
                result_json = excluded.result_json,
                error_json = excluded.error_json,
                source_json = excluded.source_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                invoice_id,
                record["status"],
                result_json,
                error_json,
                source_json,
            ),
        )


def _decode_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "status": row["status"],
        "result": json.loads(row["result_json"])
        if row["result_json"] is not None
        else None,
        "error": json.loads(row["error_json"])
        if row["error_json"] is not None
        else None,
        "source": json.loads(row["source_json"]),
    }


def get_invoice(invoice_id: str) -> dict[str, Any] | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchone()
    return _decode_record(row) if row is not None else None


def list_invoices() -> list[tuple[str, dict[str, Any]]]:
    initialize_database()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM invoices ORDER BY updated_at DESC, invoice_id"
        ).fetchall()
    return [(row["invoice_id"], _decode_record(row)) for row in rows]


def delete_invoice(invoice_id: str) -> bool:
    initialize_database()
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM invoices WHERE invoice_id = ?",
            (invoice_id,),
        )
    return cursor.rowcount > 0
