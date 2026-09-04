"""SQLite persistence for the trial change monitor.

Owns the schema and every read and write. Nothing else in the app touches SQL.

Three tables:
  trials    -- one row per watched trial
  snapshots -- one row per fetch, holding the raw registry record
  changes   -- one row per field that moved

Snapshots keep the *raw* record rather than the derived profile, so a field we
don't currently monitor is still recoverable if the team asks for it later. The
results section is stripped: results are linked to rather than tracked, and they
are the bulk of the payload.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3

# Overridable so tests and throwaway demos don't write to the working database.
DB_PATH = os.environ.get("MONITOR_DB", "monitor.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
    nct_id          TEXT PRIMARY KEY,
    monitoring_began TEXT NOT NULL,
    last_checked    TEXT,
    last_reviewed   TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id      TEXT NOT NULL REFERENCES trials(nct_id),
    fetched_at  TEXT NOT NULL,
    record      TEXT NOT NULL,
    synthetic   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS snapshots_by_trial ON snapshots(nct_id, id);

CREATE TABLE IF NOT EXISTS changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id      TEXT NOT NULL REFERENCES trials(nct_id),
    field       TEXT NOT NULL,
    previous    TEXT,
    current     TEXT,
    detected_at TEXT NOT NULL,
    synthetic   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS changes_by_trial ON changes(nct_id, id);
"""


def now() -> str:
    """Timestamp for stored rows. UTC, second precision, sorts lexically."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open the database, creating the schema if it isn't there yet."""
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# --- trials


def add_trial(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> None:
    """Start watching a trial. A trial already watched is left as it was."""
    conn.execute(
        "INSERT OR IGNORE INTO trials (nct_id, monitoring_began) VALUES (?, ?)",
        (nct_id, when or now()),
    )
    conn.commit()


def get_trial(conn: sqlite3.Connection, nct_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM trials WHERE nct_id = ?", (nct_id,)).fetchone()


def list_trials(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every watched trial, oldest first, so the list order is stable."""
    return conn.execute("SELECT * FROM trials ORDER BY monitoring_began, nct_id").fetchall()


def mark_checked(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> None:
    conn.execute(
        "UPDATE trials SET last_checked = ? WHERE nct_id = ?", (when or now(), nct_id)
    )
    conn.commit()


# --- snapshots


def strip_results(record: dict) -> dict:
    """A copy of a registry record without its results section."""
    return {k: v for k, v in record.items() if k != "resultsSection"}


def add_snapshot(
    conn: sqlite3.Connection,
    nct_id: str,
    record: dict,
    when: str | None = None,
    synthetic: bool = False,
) -> None:
    """Store a fetched record as the trial's newest snapshot."""
    conn.execute(
        "INSERT INTO snapshots (nct_id, fetched_at, record, synthetic) VALUES (?, ?, ?, ?)",
        (nct_id, when or now(), json.dumps(strip_results(record)), int(synthetic)),
    )
    conn.commit()


def latest_snapshot(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """The most recently stored record for a trial, or None if never fetched."""
    row = conn.execute(
        "SELECT record FROM snapshots WHERE nct_id = ? ORDER BY id DESC LIMIT 1",
        (nct_id,),
    ).fetchone()
    return json.loads(row["record"]) if row else None


def count_snapshots(conn: sqlite3.Connection, nct_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM snapshots WHERE nct_id = ?", (nct_id,)
    ).fetchone()["n"]


# --- changes


def list_changes(conn: sqlite3.Connection, nct_id: str | None = None) -> list[sqlite3.Row]:
    """Recorded changes, newest first. All trials unless one is named."""
    if nct_id is None:
        return conn.execute("SELECT * FROM changes ORDER BY id DESC").fetchall()
    return conn.execute(
        "SELECT * FROM changes WHERE nct_id = ? ORDER BY id DESC", (nct_id,)
    ).fetchall()
