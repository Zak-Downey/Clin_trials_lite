"""PROTOTYPE -- throwaway. Seeds a scratch database and starts the app on it.

    python prototype_card_history.py

Question: once a trial is marked reviewed its cards go clean. How should the
reader still see what moved -- the last change, recent changes, or a record per
card? Four variants of the dossier, switched with ?variant=A..D (or the bar at
the bottom of the page, or the arrow keys), on the real Watchlist page.

The database is rebuilt from the test fixture on every launch, so marking the
trial reviewed and relaunching puts the unread change back. No network.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DB = ROOT / "PROTOTYPE_card_history_wipe_me.db"
NCT = "NCT03412565"

# A story told in five checks, oldest first: the study winding down to
# completion. Each "current" is what the fixture record holds today, so the
# history lands on the profile the cards actually show.
HISTORY = [
    ("2026-06-02T09:14:00+00:00", [
        ("enrollment", 300, 280),
        ("officialTitle", "A Multicentre Phase 2 Study to Evaluate Subcutaneous "
         "Daratumumab in Combination With Standard Multiple Myeloma Treatment "
         "Regimens", None),
    ]),
    ("2026-07-14T10:02:00+00:00", [
        ("completionDate", "2024-01-31", "2024-04-18"),
        ("completionDateType", "ESTIMATED", "ACTUAL"),
    ]),
    ("2026-08-20T08:40:00+00:00", [
        ("enrollment", 280, 265),
        ("enrollmentType", "ESTIMATED", "ACTUAL"),
    ]),
    ("2026-09-19T14:25:00+00:00", [
        ("overallStatus", "ACTIVE_NOT_RECRUITING", "COMPLETED"),
        ("primaryOutcomeTimeFrames", ["Up to 2 years"], None),
    ]),
    # The one still unread: after the review on the 22nd.
    ("2026-09-26T07:55:00+00:00", [
        ("secondaryOutcomeCount", 8, 9),
    ]),
]
REVIEWED_ON = "2026-09-22T16:00:00+00:00"


def seed() -> None:
    sys.path.insert(0, str(ROOT))
    import medical_affairs
    import storage

    DB.unlink(missing_ok=True)
    conn = storage.connect(str(DB))
    record = json.loads((ROOT / "tests/fixtures/NCT03412565.json").read_text())
    profile = medical_affairs.profile(record)

    lists = storage.list_lists(conn)
    list_id = lists[0]["id"] if lists else storage.create_list(conn, "Myeloma — Janssen")
    storage.add_trial(conn, NCT, "2026-05-01T09:00:00+00:00")
    storage.add_member(conn, list_id, NCT, "2026-05-01T09:00:00+00:00")
    storage.add_snapshot(conn, NCT, record, "2026-05-01T09:00:00+00:00")

    for when, moves in HISTORY:
        for field, previous, current in moves:
            storage.add_change(
                conn,
                NCT,
                {
                    "field": field,
                    "previous": previous,
                    "current": profile.get(field) if current is None else current,
                },
                when,
            )
        storage.mark_checked(conn, NCT, when)
    conn.execute(
        "UPDATE changes SET reviewed = 1 WHERE detected_at < ?", (REVIEWED_ON,)
    )
    conn.execute("UPDATE trials SET last_reviewed = ?", (REVIEWED_ON,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
    env = {**os.environ, "MONITOR_DB": str(DB), "CARD_HISTORY_PROTOTYPE": "1"}
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py")],
        env=env,
        cwd=ROOT,
        check=False,
    )
