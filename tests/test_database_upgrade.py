"""A monitor.db written by the app before the HTML front end opens in place.

Lacks: a database older than the `reviewed` and `search` columns' own history
beyond the one shape built here.
"""

import json
import sqlite3

import storage

OLD_SCHEMA = """
CREATE TABLE trials (nct_id TEXT PRIMARY KEY, monitoring_began TEXT NOT NULL,
    last_checked TEXT, last_reviewed TEXT);
CREATE TABLE snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, nct_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL, record TEXT NOT NULL, synthetic INTEGER NOT NULL DEFAULT 0);
CREATE TABLE changes (id INTEGER PRIMARY KEY AUTOINCREMENT, nct_id TEXT NOT NULL,
    field TEXT NOT NULL, previous TEXT, current TEXT, detected_at TEXT NOT NULL,
    synthetic INTEGER NOT NULL DEFAULT 0);
"""


def test_an_older_database_opens_with_its_data_and_an_upgraded_schema(tmp_path):
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.executescript(OLD_SCHEMA)
    old.execute("INSERT INTO trials (nct_id, monitoring_began) VALUES ('NCT00000001', 'then')")
    old.execute(
        "INSERT INTO changes (nct_id, field, previous, current, detected_at)"
        " VALUES ('NCT00000001', 'enrollment', ?, ?, 'then')",
        (json.dumps(1), json.dumps(2)),
    )
    old.commit()
    old.close()

    conn = storage.connect(path)
    (trial,) = storage.list_trials(conn)
    assert trial["nct_id"] == "NCT00000001"
    (change,) = storage.list_changes(conn, "NCT00000001")
    assert (change["previous"], change["current"], change["reviewed"]) == (1, 2, False)
    # Upgraded in place: the schema version is recorded, and the trial is housed.
    assert conn.execute("PRAGMA user_version").fetchone()[0] == storage.SCHEMA_VERSION
    assert [t["nct_id"] for t in storage.list_trials(conn, 1)] == ["NCT00000001"]
