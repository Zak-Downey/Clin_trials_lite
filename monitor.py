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

    Returns a result: nct_id, an outcome of "unchanged" or "updated", and a
    detail line for the analyst. Raises MonitorError if the trial isn't watched
    or the registry can't be reached, leaving stored state untouched.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is None:
        raise MonitorError(f"{nct} is not on the watchlist.")

    record = _fetch_record(nct, fetch)
    stamp = when or storage.now()

    previous = _last_updated(storage.latest_snapshot(conn, nct))
    current = _last_updated(record)
    # An absent stamp on either side is not evidence of sameness, so only a
    # match between two real dates is allowed to short-circuit the comparison.
    if previous is not None and previous == current:
        storage.mark_checked(conn, nct, stamp)
        return {"nct_id": nct, "outcome": "unchanged", "detail": "No changes."}

    storage.add_snapshot(conn, nct, record, stamp)
    storage.mark_checked(conn, nct, stamp)
    return {
        "nct_id": nct,
        "outcome": "updated",
        "detail": "The registry record has been revised.",
    }


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
            result = {"nct_id": nct, "outcome": "error", "detail": str(exc)}
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
    record = storage.latest_snapshot(conn, nct_id)
    return medical_affairs.profile(record) if record else None


def feed(conn: sqlite3.Connection) -> list[dict]:
    """Events for the activity feed, most recent first.

    Currently one kind: a trial being added. Change entries join this feed in a
    later slice.
    """
    events = [
        {"at": t["monitoring_began"], "nct_id": t["nct_id"], "kind": "started monitoring"}
        for t in storage.list_trials(conn)
    ]
    return sorted(events, key=lambda e: e["at"], reverse=True)
