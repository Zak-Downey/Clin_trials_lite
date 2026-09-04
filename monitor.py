"""Orchestrates monitoring: adding trials, and (later) checking them for changes.

The study-fetching function is injectable and defaults to the real API call.
This is the module's only test seam -- tests pass a stub fetcher and never touch
the network.
"""

from __future__ import annotations

import re
import sqlite3
import urllib.error

import ctgov
import medical_affairs
import storage

NCT_ID = re.compile(r"^NCT\d{8}$")


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


def add(
    conn: sqlite3.Connection,
    nct_id: str,
    fetch=_default_fetch,
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

    try:
        record = fetch(nct)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise MonitorError(f"{nct} was not found on ClinicalTrials.gov.") from exc
        raise MonitorError(f"ClinicalTrials.gov returned an error for {nct} ({exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise MonitorError(f"Could not reach ClinicalTrials.gov: {exc.reason}") from exc
    except Exception as exc:
        # A timeout, a TLS failure, a malformed response. The analyst gets a
        # readable message rather than a traceback, and nothing is stored.
        raise MonitorError(f"Could not fetch {nct}: {exc}") from exc

    if not record or "protocolSection" not in record:
        raise MonitorError(f"ClinicalTrials.gov returned no usable record for {nct}.")

    stamp = when or storage.now()
    storage.add_trial(conn, nct, stamp)
    storage.add_snapshot(conn, nct, record, stamp)
    storage.mark_checked(conn, nct, stamp)
    return nct


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
