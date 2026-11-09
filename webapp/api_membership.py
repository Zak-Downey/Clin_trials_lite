"""Find trials: adding several trials to a watchlist, and the details of a trial not monitored."""

from __future__ import annotations

import display
import medical_affairs
import monitor
import storage

from .errors import ApiError

_STATUS = {"not_found": 404}


def _fetch_outside_lock(ctx, ids):
    """Fetch each ID's record with the lock released: a registry call is never made under it.

    Returns {id: record or the exception raised}; `add_many` replays them through the
    same code path that wraps a failure in a message the analyst can read.
    """
    fetch = ctx.fetch or monitor._default_fetch
    got = {}
    ctx.lock.release()
    try:
        for nct in ids:
            try:
                got[nct] = fetch(nct)
            except Exception as err:  # replayed, and worded, by monitor.add
                got[nct] = err
    finally:
        ctx.lock.acquire()
    return got


def add_trials(ctx, list_id: str, body=None, **_):
    """Add the NCT IDs sent to this watchlist; every one is attempted and reported by ID."""
    target = storage.get_list(ctx.conn, int(list_id))
    if target is None:
        raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")
    ids = (body or {}).get("nct_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ApiError(400, "invalid_request", "Send the NCT IDs to add, as a list of text.")
    needed = []
    for raw in ids:
        try:
            nct = monitor.normalise(raw)
        except monitor.MonitorError:
            continue
        if storage.get_trial(ctx.conn, nct) is None and nct not in needed:
            needed.append(nct)
    got = _fetch_outside_lock(ctx, needed)

    def replay(nct):
        value = got[nct]
        if isinstance(value, Exception):
            raise value
        return value

    outcome = monitor.add_many(ctx.conn, ids, target["id"], fetch=replay)
    outcome["list"] = {"id": target["id"], "name": target["name"]}
    del outcome["list_id"]
    return outcome


def registry_trial(ctx, nct_id: str, **_):
    """A trial's header facts and Trial details sections from one registry fetch; nothing is stored."""
    nct = nct_id.upper()
    got = _fetch_outside_lock(ctx, [nct])[nct]
    try:
        if isinstance(got, Exception):
            def raise_it(_n):
                raise got
            record = monitor._fetch_record(nct, raise_it)
        else:
            record = monitor._fetch_record(nct, lambda _n: got)
    except monitor.MonitorError as err:
        raise ApiError(_STATUS.get(err.kind, 502), err.kind, str(err))
    profile = medical_affairs.profile(record)
    body = display.detail_sections(profile)
    body.update(
        nct_id=nct,
        heading=profile.get("acronym") or profile.get("briefTitle") or nct,
        official_title=profile.get("officialTitle"),
        phase=display.phase_label(profile.get("phases")),
        sponsor=profile.get("leadSponsor"),
        status=display.status_label(profile.get("overallStatus")),
        registry_url=f"{display.STUDY_URL}/{nct}",
        watchlists=[{"id": r["id"], "name": r["name"]} for r in storage.lists_holding(ctx.conn, nct)],
    )
    return body


_LOOKUP_STATUS = {"invalid_format": 400, "not_found": 404, "already_in_list": 409, "registry_unavailable": 502}
_LOOKUP_WORDS = {
    "invalid_format": "That is not an NCT ID. Use NCT followed by 8 digits, for example NCT03275285.",
    "not_found": "No trial with that ID was found on ClinicalTrials.gov.",
    "registry_unavailable": "ClinicalTrials.gov could not be reached. Try again in a moment.",
}


def lookup(ctx, list_id: str, query=None, **_):
    """Look a trial up for this watchlist and show it before it is added; nothing is stored."""
    target = storage.get_list(ctx.conn, int(list_id))
    if target is None:
        raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")
    raw = ((query or {}).get("nct_id") or [""])[0]
    try:
        nct = monitor.normalise(raw)
        if storage.is_member(ctx.conn, target["id"], nct):
            raise monitor.MonitorError("", "already_in_list")
    except monitor.MonitorError as err:
        _lookup_failure(err, target["name"], raw)
    got = _fetch_outside_lock(ctx, [nct])[nct]

    def replay(_n):
        if isinstance(got, Exception):
            raise got
        return got

    try:
        found = monitor.lookup(ctx.conn, nct, target["id"], fetch=replay)
    except monitor.MonitorError as err:
        _lookup_failure(err, target["name"], nct)
    found["status"] = display.status_label(found["status"])
    found["list"] = {"id": target["id"], "name": target["name"]}
    return found


def _lookup_failure(err, list_name, nct):
    if err.kind == "already_in_list":
        message = f"{nct.strip().upper()} is already in {list_name}."
    else:
        message = _LOOKUP_WORDS.get(err.kind, str(err))
    raise ApiError(_LOOKUP_STATUS.get(err.kind, 502), err.kind if err.kind in _LOOKUP_STATUS else "registry_unavailable", message)
