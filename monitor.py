"""Orchestrates monitoring: adding trials, and re-checking them for changes.

The study-fetching function is injectable and defaults to the real API call.
This is the module's only test seam -- tests pass a stub fetcher and never touch
the network.
"""

from __future__ import annotations

import re
import sqlite3
import time
import urllib.error
from collections.abc import Iterator

import ctgov
import diff
import medical_affairs
import storage

NCT_ID = re.compile(r"^NCT\d{8}$")

# Seconds to wait between trials when working through the watchlist. The
# registry is a free public service; a burst of back-to-back requests is rude.
PAUSE = 0.5


class MonitorError(Exception):
    """Something went wrong that the analyst needs to see, in their words."""


def _default_fetch(nct_id: str) -> dict:
    return ctgov.get(nct_id)


def normalise(nct_id: str) -> str:
    """Tidy a pasted ID. Raises MonitorError if it isn't shaped like an NCT ID."""
    cleaned = nct_id.strip().upper()
    if not NCT_ID.match(cleaned):
        raise MonitorError(f"{nct_id.strip()!r} is not an NCT ID (expected e.g. NCT03412565).")
    return cleaned


def _fetch_record(nct: str, fetch) -> dict:
    """Fetch one study, turning every failure into a message an analyst can read.

    Nothing is stored on the way out: a failed fetch leaves the database as it was.
    """
    try:
        record = (fetch or _default_fetch)(nct)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise MonitorError(f"{nct} was not found on ClinicalTrials.gov.") from exc
        raise MonitorError(f"ClinicalTrials.gov returned an error for {nct} ({exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise MonitorError(f"Could not reach ClinicalTrials.gov: {exc.reason}") from exc
    except Exception as exc:
        # A timeout, a TLS failure, a malformed response. The analyst gets a
        # readable message rather than a traceback.
        raise MonitorError(f"Could not fetch {nct}: {exc}") from exc

    if not record or "protocolSection" not in record:
        raise MonitorError(f"ClinicalTrials.gov returned no usable record for {nct}.")
    return record


def add(
    conn: sqlite3.Connection,
    nct_id: str,
    fetch=None,
    when: str | None = None,
) -> str:
    """Start monitoring a trial, recording a baseline snapshot of its state.

    Records the baseline only: adding a trial must not report its monitored
    fields as changes. Returns the normalised NCT ID.

    Raises MonitorError -- leaving stored state untouched -- if the ID is
    malformed, unknown to the registry, or the registry can't be reached.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is not None:
        raise MonitorError(f"{nct} is already on the watchlist.")

    record = _fetch_record(nct, fetch)

    stamp = when or storage.now()
    storage.add_trial(conn, nct, stamp)
    storage.add_snapshot(conn, nct, record, stamp)
    storage.mark_checked(conn, nct, stamp)
    return nct


def _last_updated(record: dict | None) -> str | None:
    """The registry's own last-updated date for a record, if it states one."""
    if not record:
        return None
    return medical_affairs.profile(record)["lastUpdatePostDate"]


def fields_moved(count: int) -> str:
    """How many monitored fields moved, in the words the analyst reads.

    One phrase, owned here, so the watchlist, the check result and the feed
    never drift apart on how a change is described.
    """
    return f"{count} field{'' if count == 1 else 's'} changed"


def _record_changes(
    conn: sqlite3.Connection,
    nct: str,
    previous: dict | None,
    record: dict,
    when: str,
    synthetic: bool,
) -> int:
    """Store every monitored field that moved between two records.

    A trial with no earlier snapshot has nothing to be compared against, so it
    records a baseline rather than 41 changes.
    """
    if previous is None:
        return 0

    moved = diff.compare(medical_affairs.profile(previous), medical_affairs.profile(record))
    for change in moved:
        storage.add_change(conn, nct, change, when, synthetic=synthetic)
    return len(moved)


def check(
    conn: sqlite3.Connection,
    nct_id: str,
    fetch=None,
    when: str | None = None,
) -> dict:
    """Re-check one watched trial against the registry.

    The registry publishes its own last-updated date, so that is compared first:
    when it hasn't moved, nothing downstream of it can have moved either, and the
    trial is left alone but marked as checked. This keeps a check cheap as the
    watchlist grows.

    Returns a result: nct_id, an outcome of "unchanged" or "updated", the number
    of monitored fields that moved, and a detail line for the analyst. Raises
    MonitorError if the trial isn't watched or the registry can't be reached,
    leaving stored state untouched.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is None:
        raise MonitorError(f"{nct} is not on the watchlist.")

    record = _fetch_record(nct, fetch)
    stamp = when or storage.now()

    snapshot = storage.latest_snapshot(conn, nct)
    stored = snapshot["record"] if snapshot else None
    previous = _last_updated(stored)
    current = _last_updated(record)
    # An absent stamp on either side is not evidence of sameness, so only a
    # match between two real dates is allowed to short-circuit the comparison.
    if previous is not None and previous == current:
        storage.mark_checked(conn, nct, stamp)
        return {"nct_id": nct, "outcome": "unchanged", "changes": 0, "detail": "No changes."}

    # A change found against simulated history is itself simulated.
    moved = _record_changes(
        conn,
        nct,
        stored,
        record,
        stamp,
        synthetic=bool(snapshot and snapshot["synthetic"]),
    )
    storage.add_snapshot(conn, nct, record, stamp)
    storage.mark_checked(conn, nct, stamp)

    detail = (
        f"{fields_moved(moved)}."
        if moved
        else "The registry record has been revised, but no monitored field moved."
    )
    return {"nct_id": nct, "outcome": "updated", "changes": moved, "detail": detail}


def check_all(
    conn: sqlite3.Connection,
    fetch=None,
    when: str | None = None,
    pause: float = PAUSE,
) -> Iterator[dict]:
    """Re-check every watched trial, yielding one result as each finishes.

    Yielding rather than returning a list lets the page show progress while the
    run is still going. Trials are taken one at a time with a pause between
    them, and a trial that fails is reported as its own result rather than
    ending the run.
    """
    for index, trial in enumerate(storage.list_trials(conn)):
        if index:
            time.sleep(pause)
        nct = trial["nct_id"]
        try:
            result = check(conn, nct, fetch=fetch, when=when)
        except MonitorError as exc:
            result = {"nct_id": nct, "outcome": "error", "changes": 0, "detail": str(exc)}
        yield result


def summarise(results: list[dict]) -> dict:
    """Turn a completed run into the one line the analyst reads.

    A run with a failure in it is never reported as plain good news: an outage
    must not be mistaken for "nothing changed".
    """
    failed = [r for r in results if r["outcome"] == "error"]
    updated = [r for r in results if r["outcome"] == "updated"]
    checked = len(results) - len(failed)

    if failed:
        message = (
            f"Checked {checked} of {len(results)} trials. "
            f"{len(failed)} could not be reached."
        )
        level = "warning"
    elif updated:
        noun = "trial" if checked == 1 else "trials"
        message = f"Checked {checked} {noun}. {len(updated)} revised on the registry."
        level = "warning"
    else:
        noun = "trial" if checked == 1 else "trials"
        message = f"Checked {checked} {noun} — no changes."
        level = "success"

    return {"level": level, "message": message, "updated": updated, "failed": failed}


def profile_of(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """The monitored profile derived from a trial's newest stored snapshot."""
    snapshot = storage.latest_snapshot(conn, nct_id)
    return medical_affairs.profile(snapshot["record"]) if snapshot else None


def feed(conn: sqlite3.Connection) -> list[dict]:
    """Events for the activity feed, most recent first.

    The feed names trials, not fields: every field that moved in one check of
    one trial collapses into a single entry, so a sponsor revising fifteen
    fields at once doesn't bury everything else.
    """
    events = [
        {
            "at": t["monitoring_began"],
            "nct_id": t["nct_id"],
            "kind": "started monitoring",
            # Not something there is anything to review, so never flagged as new.
            "synthetic": False,
            "reviewed": True,
        }
        for t in storage.list_trials(conn)
    ]

    detections: dict[tuple[str, str], list[dict]] = {}
    for change in storage.list_changes(conn):
        detections.setdefault((change["nct_id"], change["detected_at"]), []).append(change)

    for (nct, at), changes in detections.items():
        events.append(
            {
                "at": at,
                "nct_id": nct,
                "kind": fields_moved(len(changes)),
                "synthetic": any(c["synthetic"] for c in changes),
                "reviewed": all(c["reviewed"] for c in changes),
            }
        )

    return sorted(events, key=lambda e: e["at"], reverse=True)


def marked_profile(conn: sqlite3.Connection, nct_id: str) -> dict:
    """A trial's monitored profile, marked up with what has moved.

    Returns the profile itself, for a caller wanting a field by name, one row
    per field marked with whether it moved and what it moved from, and how much
    is still awaiting review. Every field is included, not only the ones that
    moved, so a change is read in the context of the study around it.

    The outstanding count comes from the stored records rather than from the
    marked rows: a change recorded against a field since dropped from the
    monitored set has nothing left to highlight, but must still be clearable.
    """
    profile = profile_of(conn, nct_id) or {}
    return {
        "profile": profile,
        "rows": diff.annotate(profile, storage.list_changes(conn, nct_id)),
        "unreviewed": storage.count_unreviewed(conn, nct_id),
    }


def last_change(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """What moved the last time this trial changed, or None if it never has.

    One check can move several fields at once, so "the last change" is every
    field sharing the newest detection time, not just the newest recorded row.
    Fields are ordered high-signal first, so a caller showing only the first
    few of them never drops a slipped completion date in favour of a typo fix.

    Reviewed or not: the watchlist answers "what has changed on this trial",
    and a change does not stop having happened once somebody has read it. How
    much is still unread is a separate question, answered by marked_profile.
    """
    changes = storage.list_changes(conn, nct_id)
    if not changes:
        return None

    newest = changes[0]["detected_at"]
    detected = [c for c in changes if c["detected_at"] == newest]
    return {
        "at": newest,
        "fields": diff.by_signal(dict.fromkeys(c["field"] for c in detected)),
        # A detection is simulated if any part of it was.
        "synthetic": any(c["synthetic"] for c in detected),
    }


def watchlist(conn: sqlite3.Connection) -> list[dict]:
    """One row per watched trial: what identifies it, and what last moved on it.

    The whole of the watchlist table, derived here rather than in the page, so
    the table can be tested without running Streamlit and a later move off
    Streamlit rewrites only the rendering.
    """
    rows = []
    for trial in storage.list_trials(conn):
        nct = trial["nct_id"]
        profile = profile_of(conn, nct) or {}
        rows.append(
            {
                "nct_id": nct,
                "sponsor": profile.get("leadSponsor"),
                # The official title names the study; the brief title is the
                # fallback for a record that carries only one of them.
                "title": profile.get("officialTitle") or profile.get("briefTitle"),
                "phases": profile.get("phases") or [],
                "conditions": profile.get("conditions") or [],
                # The registry repeats an intervention once per arm it appears
                # in; dict.fromkeys dedupes while keeping the registry's order.
                "interventions": list(dict.fromkeys(profile.get("interventions") or [])),
                "status": profile.get("overallStatus"),
                "last_checked": trial["last_checked"],
                "last_reviewed": trial["last_reviewed"],
                "unreviewed": storage.count_unreviewed(conn, nct),
                "synthetic": storage.is_synthetic(conn, nct),
                "change": last_change(conn, nct),
            }
        )
    return rows

def review(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> int:
    """Mark a trial's outstanding changes as read, clearing its highlighting.

    Nothing is deleted: the change records are the trial's history, and a later
    move highlights it afresh. Returns how many records were marked. Raises
    MonitorError if the trial isn't watched.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is None:
        raise MonitorError(f"{nct} is not on the watchlist.")

    return storage.mark_reviewed(conn, nct, when)
