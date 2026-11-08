"""Watchlists and their Needs review queue."""

from __future__ import annotations

import display
import monitor
import storage

from .errors import ApiError
from .times import local


def _require(conn, list_id: int):
    if storage.get_list(conn, list_id) is None:
        raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")


def list_watchlists(ctx, **_):
    overview = monitor.watchlist_overview(ctx.conn)
    return {
        "watchlists": [{**w, "last_checked": local(w["last_checked"])} for w in overview]
    }


def needs_review(ctx, list_id: str, **_):
    _require(ctx.conn, int(list_id))
    entries = monitor.needs_review(ctx.conn, int(list_id))
    return {
        "trials": [
            {
                "nct_id": e["nct_id"],
                "heading": e["heading"],
                "phase": display.phase_label(e["phases"]),
                "sponsor": e["sponsor"],
                "status": display.status_label(e["status"]),
                "changed_fields": [display.label(f) for f in e["changed_fields"]],
                "detected_at": local(e["detected_at"]),
                "change_count": e["change_count"],
                "moves": e["moves"],
                "simulated": e["synthetic"],
            }
            for e in entries
        ],
        "counts": {
            "trials": len(entries),
            "field_changes": sum(e["change_count"] for e in entries),
        },
    }
