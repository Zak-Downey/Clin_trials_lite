"""Simulating a change on a trial that will never really change again.

The first test case is a completed study, so waiting for a sponsor to revise it
is not a way to demonstrate the alerting path. This module fakes the *past*
instead of the present: it rewrites a trial's stored history so the live
registry record no longer matches it, and the next ordinary check finds a
genuine difference through exactly the code real changes travel through.

The live registry therefore stays the source of truth, and everything written
here is flagged synthetic in the database so it can be removed with certainty.
The flag is a column, never text inside a stored value: marker text would
corrupt the baseline a later real change is compared against, and would turn
cleanup into string matching.
"""

from __future__ import annotations

import copy
import sqlite3

import diff
import medical_affairs
import monitor
import storage

# How far back a simulated past is wound.
REWIND_YEARS = 1

# The stored past is given a *higher* enrolment than the live record, so what
# the check then detects is a drop of this many participants.
ENROLMENT_DROP = 85


def _rewind(date: str | None) -> str | None:
    """The same date a year earlier, whether it states a day or only a month."""
    if not date:
        return None
    year, _, rest = date.partition("-")
    return f"{int(year) - REWIND_YEARS}-{rest}" if rest else str(int(year) - REWIND_YEARS)


def _alter_record(record: dict) -> dict:
    """A copy of a stored record, wound back.

    Three fields move, each chosen because its real-world equivalent is
    intelligence a medical affairs team would act on: a completion date
    slipping, enrolment falling, and a drug appearing in the arms. Nothing is
    invented -- the drug "added" is one the trial genuinely runs, removed from
    the stored past rather than fabricated into it.

    The registry's own last-updated stamp is wound back too. Without that the
    cheap pre-check would see a matching stamp and never look further.
    """
    altered = copy.deepcopy(record)
    protocol = altered.get("protocolSection", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    arms = protocol.get("armsInterventionsModule", {})

    for struct in ("completionDateStruct", "lastUpdatePostDateStruct"):
        if status.get(struct, {}).get("date"):
            status[struct]["date"] = _rewind(status[struct]["date"])

    enrolment = design.get("enrollmentInfo", {})
    if isinstance(enrolment.get("count"), int):
        enrolment["count"] += ENROLMENT_DROP

    if len(arms.get("interventions", [])) > 1:
        arms["interventions"] = arms["interventions"][:-1]

    return altered


def rewind(
    conn: sqlite3.Connection, nct_id: str, when: str | None = None
) -> dict:
    """Rewind a watched trial's stored history so the next check finds a change.

    Returns a result shaped like a check's: the trial, the profile fields now
    differing from the record last fetched, and a line to show whoever pressed
    the button.
    Field names are the profile's own, since the audience here is a developer.
    Raises MonitorError if the trial isn't watched or has no stored state yet.
    """
    nct = monitor.normalise(nct_id)

    snapshot = storage.latest_snapshot(conn, nct)
    if storage.get_trial(conn, nct) is None or snapshot is None:
        raise monitor.MonitorError(f"{nct} is not on the watchlist.")

    altered = _alter_record(snapshot["record"])
    # What moved is read off the same comparison a check uses, rather than
    # predicted from the edits above: winding one raw field back can move more
    # than one derived profile field.
    moved = [
        change["field"]
        for change in diff.compare(
            medical_affairs.profile(snapshot["record"]), medical_affairs.profile(altered)
        )
    ]
    storage.add_snapshot(conn, nct, altered, when, synthetic=True)
    return {
        "nct_id": nct,
        "fields": moved,
        "detail": (
            f"Rewound {nct}'s stored history: "
            f"{', '.join(moved)} now differ from the last record fetched."
        ),
    }
