"""SQLite persistence for the trial change monitor.

Owns the schema and every read and write. Nothing else in the app touches SQL.

Five tables:
  lists        -- one row per named watchlist
  list_members -- which trials a list holds
  trials       -- one row per watched trial
  snapshots    -- one row per fetch, holding the raw registry record
  changes      -- one row per field that moved

Membership is its own table rather than a column on the trial, because someone
covering two overlapping indications sees the same study in both lists and
taking it out of one must leave the other alone.

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

# What a database with no lists of its own gets called, both on a first run and
# when one written before lists existed is opened.
DEFAULT_LIST = "My watchlist"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lists (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    created TEXT NOT NULL
);

-- The name is how the reader tells two lists apart, so the database enforces
-- it rather than trusting every caller to check first.
CREATE UNIQUE INDEX IF NOT EXISTS lists_by_name ON lists(name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS list_members (
    list_id INTEGER NOT NULL REFERENCES lists(id),
    nct_id  TEXT NOT NULL REFERENCES trials(nct_id),
    added   TEXT NOT NULL,
    PRIMARY KEY (list_id, nct_id)
);

CREATE INDEX IF NOT EXISTS members_by_trial ON list_members(nct_id);

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
    synthetic   INTEGER NOT NULL DEFAULT 0,
    reviewed    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS changes_by_trial ON changes(nct_id, id);
"""


def now() -> str:
    """Timestamp for stored rows. UTC, second precision, sorts lexically."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# Columns added to the schema after databases existed in the wild. CREATE TABLE
# IF NOT EXISTS leaves an older table as it was, so they are added on connect.
LATE_COLUMNS = (("changes", "reviewed", "INTEGER NOT NULL DEFAULT 0"),)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add any column a database predating it is missing."""
    for table, column, declaration in LATE_COLUMNS:
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    conn.commit()


def _house_every_trial(conn: sqlite3.Connection) -> None:
    """Give a database with no lists of its own one, holding everything it has.

    A database written before lists existed has trials belonging nowhere; they
    all join a single default list, so nobody has to re-add a trial. The same
    step gives a brand-new database one list to stand in, since the watchlist
    page always shows a list and there has to be one to choose.

    It runs once, on the first connect that finds no lists. A database already
    using lists is never touched.
    """
    if conn.execute("SELECT 1 FROM lists LIMIT 1").fetchone():
        return

    stamp = now()
    home = conn.execute(
        "INSERT INTO lists (name, created) VALUES (?, ?)", (DEFAULT_LIST, stamp)
    ).lastrowid
    # Only ever the trials of a database that had no lists at all. A trial that
    # loses its last list while the app is running is deliberately dropped, and
    # re-homing it here would quietly undo that.
    conn.execute(
        "INSERT INTO list_members (list_id, nct_id, added) SELECT ?, nct_id, ? FROM trials",
        (home, stamp),
    )
    conn.commit()


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open the database, creating the schema if it isn't there yet."""
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    _house_every_trial(conn)
    return conn


# --- lists


def create_list(conn: sqlite3.Connection, name: str, when: str | None = None) -> int:
    """Make a new named list and return its id.

    Raises sqlite3.IntegrityError if the name is taken; monitor turns that into
    something the reader can act on.
    """
    cursor = conn.execute(
        "INSERT INTO lists (name, created) VALUES (?, ?)", (name, when or now())
    )
    conn.commit()
    return cursor.lastrowid


def list_lists(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every list, oldest first, so the order the reader sees is stable."""
    return conn.execute("SELECT * FROM lists ORDER BY id").fetchall()


def get_list(conn: sqlite3.Connection, list_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()


def find_list(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    """The list with this name, matched the way the unique index matches."""
    return conn.execute(
        "SELECT * FROM lists WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()


def rename_list(conn: sqlite3.Connection, list_id: int, name: str) -> None:
    """Give a list a different name. What it holds is untouched."""
    conn.execute("UPDATE lists SET name = ? WHERE id = ?", (name, list_id))
    conn.commit()


def delete_list(conn: sqlite3.Connection, list_id: int) -> None:
    """Remove a list and its membership rows. The trials themselves stay."""
    conn.execute("DELETE FROM list_members WHERE list_id = ?", (list_id,))
    conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
    conn.commit()


# --- membership


def add_member(
    conn: sqlite3.Connection, list_id: int, nct_id: str, when: str | None = None
) -> None:
    """Put a trial in a list. A trial already in it is left as it was."""
    conn.execute(
        "INSERT OR IGNORE INTO list_members (list_id, nct_id, added) VALUES (?, ?, ?)",
        (list_id, nct_id, when or now()),
    )
    conn.commit()


def remove_member(conn: sqlite3.Connection, list_id: int, nct_id: str) -> None:
    conn.execute(
        "DELETE FROM list_members WHERE list_id = ? AND nct_id = ?", (list_id, nct_id)
    )
    conn.commit()


def is_member(conn: sqlite3.Connection, list_id: int, nct_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM list_members WHERE list_id = ? AND nct_id = ?",
            (list_id, nct_id),
        ).fetchone()
        is not None
    )


def lists_holding(conn: sqlite3.Connection, nct_id: str) -> list[sqlite3.Row]:
    """Every list a trial belongs to, oldest list first."""
    return conn.execute(
        "SELECT lists.* FROM lists JOIN list_members ON list_members.list_id = lists.id"
        " WHERE list_members.nct_id = ? ORDER BY lists.id",
        (nct_id,),
    ).fetchall()


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


def list_trials(conn: sqlite3.Connection, list_id: int | None = None) -> list[sqlite3.Row]:
    """Watched trials, oldest first, so the order is stable.

    Everything monitored, or only what one named list holds.
    """
    if list_id is None:
        return conn.execute("SELECT * FROM trials ORDER BY monitoring_began, nct_id").fetchall()
    return conn.execute(
        "SELECT trials.* FROM trials"
        " JOIN list_members ON list_members.nct_id = trials.nct_id"
        " WHERE list_members.list_id = ?"
        " ORDER BY trials.monitoring_began, trials.nct_id",
        (list_id,),
    ).fetchall()


def delete_trial(conn: sqlite3.Connection, nct_id: str) -> None:
    """Stop monitoring a trial, taking its history with it.

    Only reached once no list holds the trial any more, so nothing is left
    pointing at it.
    """
    conn.execute("DELETE FROM list_members WHERE nct_id = ?", (nct_id,))
    conn.execute("DELETE FROM changes WHERE nct_id = ?", (nct_id,))
    conn.execute("DELETE FROM snapshots WHERE nct_id = ?", (nct_id,))
    conn.execute("DELETE FROM trials WHERE nct_id = ?", (nct_id,))
    conn.commit()


def mark_checked(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> None:
    conn.execute(
        "UPDATE trials SET last_checked = ? WHERE nct_id = ?", (when or now(), nct_id)
    )
    conn.commit()


def mark_reviewed(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> int:
    """Mark everything so far detected on a trial as seen. Returns how many rows.

    The rows are kept and flagged rather than deleted: they are the trial's
    history, and only the highlighting is being cleared.
    """
    stamp = when or now()
    marked = conn.execute(
        "UPDATE changes SET reviewed = 1 WHERE nct_id = ? AND reviewed = 0", (nct_id,)
    ).rowcount
    conn.execute("UPDATE trials SET last_reviewed = ? WHERE nct_id = ?", (stamp, nct_id))
    conn.commit()
    return marked


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
    """A trial's most recently stored state, or None if it was never fetched.

    Returns the record together with whether it was written by the simulator,
    since a change found against a simulated baseline is itself simulated.
    """
    row = conn.execute(
        "SELECT * FROM snapshots WHERE nct_id = ? ORDER BY id DESC LIMIT 1",
        (nct_id,),
    ).fetchone()
    if row is None:
        return None
    return {"record": json.loads(row["record"]), "synthetic": bool(row["synthetic"])}


def count_snapshots(conn: sqlite3.Connection, nct_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM snapshots WHERE nct_id = ?", (nct_id,)
    ).fetchone()["n"]


# --- changes


def add_change(
    conn: sqlite3.Connection,
    nct_id: str,
    change: dict,
    when: str | None = None,
    synthetic: bool = False,
) -> None:
    """Record one field that moved, as reported by the comparison.

    Values are stored as JSON so a list comes back as a list rather than as its
    printed form.
    """
    conn.execute(
        "INSERT INTO changes (nct_id, field, previous, current, detected_at, synthetic)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            nct_id,
            change["field"],
            json.dumps(change["previous"]),
            json.dumps(change["current"]),
            when or now(),
            int(synthetic),
        ),
    )
    conn.commit()


def list_changes(conn: sqlite3.Connection, nct_id: str | None = None) -> list[dict]:
    """Recorded changes, newest first. All trials unless one is named."""
    if nct_id is None:
        rows = conn.execute("SELECT * FROM changes ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM changes WHERE nct_id = ? ORDER BY id DESC", (nct_id,)
        ).fetchall()
    return [
        {
            "nct_id": row["nct_id"],
            "field": row["field"],
            "previous": json.loads(row["previous"]),
            "current": json.loads(row["current"]),
            "detected_at": row["detected_at"],
            "synthetic": bool(row["synthetic"]),
            "reviewed": bool(row["reviewed"]),
        }
        for row in rows
    ]


def count_unreviewed(conn: sqlite3.Connection, nct_id: str) -> int:
    """How many of a trial's recorded changes have not been marked as read."""
    return conn.execute(
        "SELECT COUNT(*) AS n FROM changes WHERE nct_id = ? AND reviewed = 0", (nct_id,)
    ).fetchone()["n"]


# --- synthetic data


def is_synthetic(conn: sqlite3.Connection, nct_id: str) -> bool:
    """Whether what a trial currently shows was fabricated by the simulator.

    True while its newest stored state is a simulated one, and while any change
    found against such a state is still recorded.
    """
    row = conn.execute(
        "SELECT (SELECT synthetic FROM snapshots WHERE nct_id = ?1"
        "        ORDER BY id DESC LIMIT 1) AS newest,"
        "       (SELECT COUNT(*) FROM changes WHERE nct_id = ?1 AND synthetic = 1) AS found",
        (nct_id,),
    ).fetchone()
    return bool(row["newest"]) or bool(row["found"])


def delete_synthetic(conn: sqlite3.Connection) -> int:
    """Remove everything the simulator caused to be written, in one operation.

    The flag is a column rather than text inside a value, so this is a delete by
    predicate rather than string matching, and real data is untouched. Returns
    the number of rows removed.
    """
    removed = conn.execute("DELETE FROM changes WHERE synthetic = 1").rowcount
    removed += conn.execute("DELETE FROM snapshots WHERE synthetic = 1").rowcount
    conn.commit()
    return removed
