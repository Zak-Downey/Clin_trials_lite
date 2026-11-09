"""A watchlist's saved search: read, save or replace, turn off."""

from __future__ import annotations

import monitor
import storage

from .api_watchlists import _require, list_watchlists
from .errors import ApiError

_TEXT = ("cond", "intr", "spons", "started_from", "started_to")
_LISTS = ("phase", "sponsor_type", "status")


def _for_page(stored: dict | None):
    """The stored query in the page's axis names (phase, sponsor_type, status)."""
    if stored is None:
        return None
    return {
        "cond": stored.get("cond", ""), "intr": stored.get("intr", ""), "spons": stored.get("spons", ""),
        "phase": list(stored.get("phases", [])), "sponsor_type": list(stored.get("sponsor_types", [])),
        "status": list(stored.get("statuses", [])),
        "started_from": stored.get("started_from", ""), "started_to": stored.get("started_to", ""),
    }


def _read_query(body) -> dict:
    sent = (body or {}).get("query")
    bad = ApiError(400, "invalid_request", "Send the search to save as a query.")
    if not isinstance(sent, dict):
        raise bad
    if not all(isinstance(sent.get(k, ""), str) for k in _TEXT):
        raise bad
    if not all(isinstance(sent.get(k, []), list) and all(isinstance(v, str) for v in sent.get(k, [])) for k in _LISTS):
        raise bad
    return monitor.as_query(
        cond=sent.get("cond", ""), intr=sent.get("intr", ""), spons=sent.get("spons", ""),
        phases=sent.get("phase", []), sponsor_types=sent.get("sponsor_type", []),
        statuses=sent.get("status", []),
        started_from=sent.get("started_from", ""), started_to=sent.get("started_to", ""),
    )


def read(ctx, list_id: str, **_):
    _require(ctx.conn, int(list_id))
    return {"saved_search": _for_page(monitor.remembered_search(ctx.conn, int(list_id)))}


def save(ctx, list_id: str, body=None, **_):
    """Save or replace the watchlist's one saved search. Adds no trials."""
    _require(ctx.conn, int(list_id))
    query = _read_query(body)
    previous = monitor.remembered_search(ctx.conn, int(list_id))
    try:
        stored = monitor.remember_search(ctx.conn, int(list_id), query)
    except monitor.MonitorError as err:
        raise ApiError(400, err.kind, str(err))
    target = storage.get_list(ctx.conn, int(list_id))
    return {
        "watchlist": {"id": target["id"], "name": target["name"]},
        "saved_search": _for_page(stored), "previous": _for_page(previous),
        "replaced": previous is not None,
        "watchlists": list_watchlists(ctx)["watchlists"],
    }


def turn_off(ctx, list_id: str, **_):
    """Stop the saved search; every trial stays."""
    _require(ctx.conn, int(list_id))
    monitor.forget_search(ctx.conn, int(list_id))
    return {"watchlists": list_watchlists(ctx)["watchlists"]}
