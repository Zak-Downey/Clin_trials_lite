"""SQLite persistence for the trial change monitor.

Owns the schema and every read and write. Nothing else in the app touches SQL.

Six tables:
  lists        -- one row per named watchlist, and the search it remembers
  list_members -- which trials a list holds
  found        -- trials a list's remembered search turned up, awaiting a verdict
  trials       -- one row per watched trial
  snapshots    -- one row per fetch, holding the raw registry record
  changes      -- one row per field that moved

A found trial is deliberately not a row in `trials`: it is a study offered to
the analyst, not one being monitored, and it becomes the second only when they
adopt it.

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
-- `search` holds the query the list re-runs on every check, as the four axes
-- it was typed on, or NULL for a list watching only what it already holds.
CREATE TABLE IF NOT EXISTS lists (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    created TEXT NOT NULL,
    search  TEXT
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

-- Trials a list's remembered search matched that the list does not hold. The
-- record found is kept so the offer can be read on the same facts a watched
-- trial is listed by without going back to the registry. A dismissed row stays
-- rather than being deleted: it is what stops the trial being offered again.
CREATE TABLE IF NOT EXISTS found (
    list_id   INTEGER NOT NULL REFERENCES lists(id),
    nct_id    TEXT NOT NULL,
    record    TEXT NOT NULL,
    found_at  TEXT NOT NULL,
    dismissed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (list_id, nct_id)
);

CREATE INDEX IF NOT EXISTS found_by_list ON found(list_id, found_at);

CREATE TABLE IF NOT EXISTS trials (
    nct_id          TEXT PRIMARY KEY,
    monitoring_began TEXT NOT NULL,
    last_checked    TEXT,
    last_reviewed   TEXT
);

-- When monitoring of a trial stopped (its last watchlist let it go) and resumed
-- (a watchlist took it back), so History can show the gap as "not watched".
CREATE TABLE IF NOT EXISTS monitoring_events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id TEXT NOT NULL REFERENCES trials(nct_id),
    kind   TEXT NOT NULL,
    at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS monitoring_by_trial ON monitoring_events(nct_id, id);

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

-- Each review of a trial: when, and exactly which change IDs it marked. An undo
-- stamps `undone_at` on the event it reverses rather than deleting it.
CREATE TABLE IF NOT EXISTS review_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id      TEXT NOT NULL REFERENCES trials(nct_id),
    reviewed_at TEXT NOT NULL,
    change_ids  TEXT NOT NULL,
    undone_at   TEXT
);
"""


def now() -> str:
    """Timestamp for stored rows. UTC, second precision, sorts lexically."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# Columns added to the schema after databases existed in the wild. CREATE TABLE
# IF NOT EXISTS leaves an older table as it was, so they are added on connect.
LATE_COLUMNS = (
    ("changes", "reviewed", "INTEGER NOT NULL DEFAULT 0"),
    ("lists", "search", "TEXT"),
    # A failed check, kept apart from `last_checked` (the last *successful* one).
    ("trials", "check_failed_at", "TEXT"),
    ("trials", "check_error_kind", "TEXT"),
    # When a list's most recent check for updates finished, and which trials
    # failed in it (a JSON list of NCT IDs): what "Retry failed" re-checks.
    ("lists", "last_check_finished", "TEXT"),
    ("lists", "last_check_failed", "TEXT"),
    # Whether the saved search's last run matched more than the cap of new matches.
    ("lists", "search_capped", "INTEGER NOT NULL DEFAULT 0"),
)


# Recorded in the file (PRAGMA user_version) each time it is opened, so a
# database written by an older app is known to have been upgraded in place.
SCHEMA_VERSION = 2


def _migrate(conn: sqlite3.Connection) -> None:
    """Add any column a database predating it is missing."""
    for table, column, declaration in LATE_COLUMNS:
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    # A file written by a later app keeps its later version.
    if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
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
    # Not a trial left unwatched on purpose: its removal is recorded and stays.
    conn.execute(
        "INSERT INTO list_members (list_id, nct_id, added) SELECT ?, nct_id, ? FROM trials"
        " WHERE nct_id NOT IN (SELECT nct_id FROM monitoring_events WHERE kind = 'stopped')",
        (home, stamp),
    )
    conn.commit()


def connect(path: str | None = None, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open the database, creating the schema if it isn't there yet."""
    conn = sqlite3.connect(path or DB_PATH, check_same_thread=check_same_thread)
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
    """Remove a list, its membership rows and anything it had on offer.

    The trials themselves stay, history and all; one no other list holds
    becomes unmonitored.
    """
    held = [r["nct_id"] for r in conn.execute(
        "SELECT nct_id FROM list_members WHERE list_id = ?", (list_id,))]
    conn.execute("DELETE FROM list_members WHERE list_id = ?", (list_id,))
    for nct in held:
        _note_if_unheld(conn, nct)
    conn.execute("DELETE FROM found WHERE list_id = ?", (list_id,))
    conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
    conn.commit()


def set_list_search(conn: sqlite3.Connection, list_id: int, search: dict | None) -> None:
    """Give a list the search it re-runs on every check, or take it away."""
    conn.execute(
        "UPDATE lists SET search = ?, search_capped = 0 WHERE id = ?",
        (json.dumps(search) if search else None, list_id),
    )
    conn.commit()


def set_search_capped(conn: sqlite3.Connection, list_id: int, capped: bool) -> None:
    """Record whether the saved search's latest run matched more than it could offer."""
    conn.execute("UPDATE lists SET search_capped = ? WHERE id = ?", (int(capped), list_id))
    conn.commit()


def search_capped(conn: sqlite3.Connection, list_id: int) -> bool:
    row = conn.execute("SELECT search_capped FROM lists WHERE id = ?", (list_id,)).fetchone()
    return bool(row and row["search_capped"])


def get_list_search(conn: sqlite3.Connection, list_id: int) -> dict | None:
    """The search a list remembers, or None if it remembers none."""
    row = conn.execute("SELECT search FROM lists WHERE id = ?", (list_id,)).fetchone()
    return json.loads(row["search"]) if row and row["search"] else None


# --- membership


def add_member(
    conn: sqlite3.Connection, list_id: int, nct_id: str, when: str | None = None
) -> None:
    """Put a trial in a list. A trial already in it is left as it was.

    A trial no list was holding is monitored again from here: that is recorded.
    """
    if get_trial(conn, nct_id) is not None and not lists_holding(conn, nct_id):
        last = conn.execute(
            "SELECT kind FROM monitoring_events WHERE nct_id = ? ORDER BY id DESC LIMIT 1",
            (nct_id,),
        ).fetchone()
        if last and last["kind"] == "stopped":
            conn.execute(
                "INSERT INTO monitoring_events (nct_id, kind, at) VALUES (?, 'resumed', ?)",
                (nct_id, when or now()),
            )
    conn.execute(
        "INSERT OR IGNORE INTO list_members (list_id, nct_id, added) VALUES (?, ?, ?)",
        (list_id, nct_id, when or now()),
    )
    conn.commit()


def _note_if_unheld(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> int | None:
    """Record that monitoring stopped if no list holds the trial now. Returns the event id."""
    if lists_holding(conn, nct_id):
        return None
    return conn.execute(
        "INSERT INTO monitoring_events (nct_id, kind, at) VALUES (?, 'stopped', ?)",
        (nct_id, when or now()),
    ).lastrowid


def remove_member(
    conn: sqlite3.Connection, list_id: int, nct_id: str, when: str | None = None
) -> int | None:
    """Take a trial out of a list. Returns the id of the 'stopped' event when that
    left the trial in no list (its history is kept, it is no longer checked)."""
    conn.execute(
        "DELETE FROM list_members WHERE list_id = ? AND nct_id = ?", (list_id, nct_id)
    )
    stopped = _note_if_unheld(conn, nct_id, when)
    conn.commit()
    return stopped


def monitoring_events(conn: sqlite3.Connection, nct_id: str) -> list[dict]:
    """When monitoring of a trial stopped and resumed, oldest first."""
    return [
        {"id": r["id"], "kind": r["kind"], "at": r["at"]}
        for r in conn.execute(
            "SELECT * FROM monitoring_events WHERE nct_id = ? ORDER BY id", (nct_id,))
    ]


def forget_monitoring_event(conn: sqlite3.Connection, event_id: int) -> None:
    """Drop one monitoring event (an undone removal leaves no gap behind)."""
    conn.execute("DELETE FROM monitoring_events WHERE id = ?", (event_id,))
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


# --- found trials
#
# A study a list's remembered search matched and the list does not hold. It sits
# here until the analyst adopts it -- at which point it becomes an ordinary
# watched trial -- or dismisses it, which leaves the row behind, flagged, so the
# same study is never offered to that list twice.


def add_found(
    conn: sqlite3.Connection,
    list_id: int,
    nct_id: str,
    record: dict,
    when: str | None = None,
) -> None:
    """Offer a trial to a list. One already offered is left exactly as it was.

    Left as it was rather than refreshed: the row carries when the study was
    first seen and whether it has already been turned down, and re-running the
    search must not reset either.
    """
    conn.execute(
        "INSERT OR IGNORE INTO found (list_id, nct_id, record, found_at)"
        " VALUES (?, ?, ?, ?)",
        (list_id, nct_id, json.dumps(strip_results(record)), when or now()),
    )
    conn.commit()


def has_been_found(conn: sqlite3.Connection, list_id: int, nct_id: str) -> bool:
    """Whether this list has already been offered this trial, dismissed or not."""
    return (
        conn.execute(
            "SELECT 1 FROM found WHERE list_id = ? AND nct_id = ?", (list_id, nct_id)
        ).fetchone()
        is not None
    )


def _found(row: sqlite3.Row) -> dict:
    return {
        "list_id": row["list_id"],
        "nct_id": row["nct_id"],
        "record": json.loads(row["record"]),
        "found_at": row["found_at"],
        "dismissed": bool(row["dismissed"]),
    }


def list_found(
    conn: sqlite3.Connection, list_id: int | None = None, dismissed: bool | None = False
) -> list[dict]:
    """Trials on offer, oldest first. One list's, or every list's.

    `dismissed` selects which verdicts to include: False for what is still
    waiting, True for what has been turned down, None for both.
    """
    where, params = [], []
    if list_id is not None:
        where.append("list_id = ?")
        params.append(list_id)
    if dismissed is not None:
        where.append("dismissed = ?")
        params.append(int(dismissed))
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"SELECT * FROM found{clause} ORDER BY found_at, nct_id", params
    ).fetchall()
    return [_found(row) for row in rows]


def dismiss_found(conn: sqlite3.Connection, list_id: int, nct_id: str) -> None:
    """Turn an offered trial down. The row stays, so it is not offered again."""
    conn.execute(
        "UPDATE found SET dismissed = 1 WHERE list_id = ? AND nct_id = ?",
        (list_id, nct_id),
    )
    conn.commit()


def restore_found(conn: sqlite3.Connection, list_id: int, nct_id: str) -> bool:
    """Offer a dismissed trial again. True if it was dismissed."""
    done = conn.execute(
        "UPDATE found SET dismissed = 0 WHERE list_id = ? AND nct_id = ? AND dismissed = 1",
        (list_id, nct_id),
    )
    conn.commit()
    return done.rowcount > 0


def delete_found(conn: sqlite3.Connection, list_id: int, nct_id: str) -> None:
    """Take a trial off offer, because it is now in the list.

    Deleted rather than flagged: membership itself is what keeps the search
    from offering it again, and a row here would be a second, staler record of
    the same fact.

    So a trial adopted and later taken out of the list is offered afresh the
    next time the search matches it, which is right: removing it says it does
    not belong in the list today, not that it should never be raised again.
    Saying that is what dismissing is for, and a dismissed row is kept.
    """
    conn.execute(
        "DELETE FROM found WHERE list_id = ? AND nct_id = ?", (list_id, nct_id)
    )
    conn.commit()


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
        # Only what some list holds: a trial in none is kept but not monitored.
        return conn.execute(
            "SELECT * FROM trials WHERE nct_id IN (SELECT nct_id FROM list_members)"
            " ORDER BY monitoring_began, nct_id"
        ).fetchall()
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
    conn.execute("DELETE FROM monitoring_events WHERE nct_id = ?", (nct_id,))
    conn.execute("DELETE FROM review_events WHERE nct_id = ?", (nct_id,))
    conn.execute("DELETE FROM trials WHERE nct_id = ?", (nct_id,))
    conn.commit()


def mark_checked(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> None:
    """Record a successful check, which clears any failure recorded against the trial."""
    conn.execute(
        "UPDATE trials SET last_checked = ?, check_failed_at = NULL, check_error_kind = NULL"
        " WHERE nct_id = ?",
        (when or now(), nct_id),
    )
    conn.commit()


def mark_check_failed(
    conn: sqlite3.Connection, nct_id: str, kind: str, when: str | None = None
) -> None:
    """Record that a check failed, without moving the last successful check."""
    conn.execute(
        "UPDATE trials SET check_failed_at = ?, check_error_kind = ? WHERE nct_id = ?",
        (when or now(), kind, nct_id),
    )
    conn.commit()


def finish_check_run(
    conn: sqlite3.Connection, list_id: int, failed: list[str], when: str | None = None
) -> None:
    """Record that a list's check for updates finished, and which trials failed in it."""
    conn.execute(
        "UPDATE lists SET last_check_finished = ?, last_check_failed = ? WHERE id = ?",
        (when or now(), json.dumps(sorted(failed)), list_id),
    )
    conn.commit()


def last_check_run(conn: sqlite3.Connection, list_id: int) -> dict:
    """{"finished": stamp or None, "failed": [NCT IDs]} for a list's last check run."""
    row = conn.execute(
        "SELECT last_check_finished, last_check_failed FROM lists WHERE id = ?", (list_id,)
    ).fetchone()
    if row is None:
        return {"finished": None, "failed": []}
    return {
        "finished": row["last_check_finished"],
        "failed": json.loads(row["last_check_failed"] or "[]"),
    }


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


def _event(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "nct_id": row["nct_id"],
        "reviewed_at": row["reviewed_at"],
        "change_ids": json.loads(row["change_ids"]),
        "undone_at": row["undone_at"],
    }


def review_changes(
    conn: sqlite3.Connection, nct_id: str, ids: list[int], when: str | None = None
) -> dict | None:
    """Mark exactly these change IDs of a trial reviewed and record the review.

    An ID that is not an unreviewed change of this trial is left alone. Returns
    the review event (its `change_ids` are what was marked), or None when
    nothing was.
    """
    stamp = when or now()
    wanted = sorted({int(i) for i in ids})
    marks = ",".join("?" * len(wanted))
    marked = [
        row["id"]
        for row in conn.execute(
            f"SELECT id FROM changes WHERE nct_id = ? AND reviewed = 0 AND id IN ({marks}) ORDER BY id",
            (nct_id, *wanted),
        )
    ] if wanted else []
    if not marked:
        return None
    conn.execute(
        f"UPDATE changes SET reviewed = 1 WHERE id IN ({','.join('?' * len(marked))})", marked
    )
    conn.execute("UPDATE trials SET last_reviewed = ? WHERE nct_id = ?", (stamp, nct_id))
    event_id = conn.execute(
        "INSERT INTO review_events (nct_id, reviewed_at, change_ids) VALUES (?, ?, ?)",
        (nct_id, stamp, json.dumps(marked)),
    ).lastrowid
    conn.commit()
    return _event(conn.execute("SELECT * FROM review_events WHERE id = ?", (event_id,)).fetchone())


def review_events(conn: sqlite3.Connection, nct_id: str) -> list[dict]:
    """Every review of a trial, oldest first, undone ones included."""
    return [
        _event(r) for r in conn.execute(
            "SELECT * FROM review_events WHERE nct_id = ? ORDER BY id", (nct_id,))
    ]


def get_review_event(conn: sqlite3.Connection, event_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM review_events WHERE id = ?", (event_id,)).fetchone()
    return _event(row) if row else None


def undo_review(conn: sqlite3.Connection, event_id: int, when: str | None = None) -> dict | None:
    """Return exactly the changes a review marked to unreviewed and record the undo.

    None if there is no such event or it was already undone.
    """
    event = get_review_event(conn, event_id)
    if event is None or event["undone_at"]:
        return None
    ids = event["change_ids"]
    conn.execute(
        f"UPDATE changes SET reviewed = 0 WHERE id IN ({','.join('?' * len(ids))})", ids
    )
    conn.execute(
        "UPDATE review_events SET undone_at = ? WHERE id = ?", (when or now(), event_id)
    )
    conn.commit()
    return get_review_event(conn, event_id)


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


def _snapshot(row: sqlite3.Row | None) -> dict | None:
    """A stored snapshot row as the record and how it came to be written."""
    if row is None:
        return None
    return {"record": json.loads(row["record"]), "synthetic": bool(row["synthetic"])}


def latest_snapshot(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """A trial's most recently stored state, or None if it was never fetched.

    Returns the record together with whether it was written by the simulator,
    since a change found against a simulated baseline is itself simulated.

    The newest row rather than the newest stamp: the simulator writes a
    rewound past, and what the next check compares against is the last thing
    stored, not the latest moment recorded.
    """
    return _snapshot(
        conn.execute(
            "SELECT * FROM snapshots WHERE nct_id = ? ORDER BY id DESC LIMIT 1",
            (nct_id,),
        ).fetchone()
    )


def snapshot_at(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> dict | None:
    """The trial's stored state as of a moment: the newest fetched by then.

    A check writes its snapshot and its change rows under one stamp, so this
    answers "what did the record say when this was detected" -- which is what
    dates a change by the sponsor's own revision rather than by whatever the
    trial says today.

    Ordered by the stamp rather than by the row's id, because the stamp is
    passed in: a snapshot written for an earlier moment than the one before it
    is ordered by the moment it records.
    """
    if when is None:
        return latest_snapshot(conn, nct_id)
    return _snapshot(
        conn.execute(
            "SELECT * FROM snapshots WHERE nct_id = ? AND fetched_at <= ?"
            " ORDER BY fetched_at DESC, id DESC LIMIT 1",
            (nct_id, when),
        ).fetchone()
    )


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
            "id": row["id"],
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
