"""Find trials: one page of a registry search."""

from __future__ import annotations

import display
import monitor

from .errors import ApiError


def search(ctx, query: dict, **_):
    def one(name):
        return (query.get(name) or [""])[0]

    try:
        page = int(one("page") or 1)
    except ValueError:
        page = 0
    if not 1 <= page <= monitor.SEARCH_CAP // monitor.PAGE_SIZE:
        raise ApiError(400, "bad_page", "Page must be a number from 1 to 10.")
    args = dict(
        cond=one("cond"), intr=one("intr"), spons=one("spons"),
        phases=query.get("phase", []), sponsor_types=query.get("sponsor_type", []),
        statuses=query.get("status", []),
        started_from=one("started_from"), started_to=one("started_to"),
    )
    try:
        monitor._refuse_unanswerable(monitor.as_query(**args))
    except monitor.MonitorError as err:
        raise ApiError(400, err.kind, str(err))
    # The lock is held by the dispatcher; the registry call is not made under it.
    ctx.lock.release()
    try:
        found = monitor.search_page(**args, page=page, find_page=ctx.find_page)
    except monitor.MonitorError as err:
        raise ApiError(502, "registry_error", str(err))
    finally:
        ctx.lock.acquire()
    found["rows"] = [
        {
            "nct_id": r["nct_id"],
            "title": r["title"],
            "sponsor": r["sponsor"],
            "phase": display.phase_label(r["phases"]),
            "status": display.status_label(r["status"]),
            "conditions": r["conditions"],
            "interventions": r["interventions"],
        }
        for r in found["rows"]
    ]
    return found
