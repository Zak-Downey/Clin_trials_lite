"""New matches: what a watchlist's saved search found that it does not monitor.

Adding them is the ordinary add (`POST /api/watchlists/<id>/trials`), which also takes
them off the offer. Dismissing keeps a flagged row, so a later check does not offer the
trial again to this watchlist; restoring clears the flag.
"""

from __future__ import annotations

import display
import monitor
import storage

from .api_watchlists import _require
from .errors import ApiError


def _rows(ctx, list_id: int, dismissed: bool) -> list[dict]:
    rows = []
    for r in monitor.found_trials(ctx.conn, list_id, dismissed=dismissed):
        rows.append({
            "nct_id": r["nct_id"],
            "heading": r["title"] or r["nct_id"],
            "phase": display.phase_label(r["phases"]),
            "sponsor": r["sponsor"],
            "status": display.status_label(r["status"]),
        })
    return rows


def _ids(body) -> list[str]:
    ids = (body or {}).get("nct_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ApiError(400, "invalid_request", "Send the NCT IDs as a list of text.")
    clean = []
    for raw in ids:
        try:
            nct = monitor.normalise(raw)
        except monitor.MonitorError:
            continue
        if nct not in clean:
            clean.append(nct)
    return clean


def read(ctx, list_id: str, **_):
    _require(ctx.conn, int(list_id))
    trials = _rows(ctx, int(list_id), False)
    return {
        "trials": trials,
        "counts": {"trials": len(trials)},
        "capped": storage.search_capped(ctx.conn, int(list_id)),
        "cap": monitor.RESULT_CAP,
        "saved_search": monitor.remembered_search(ctx.conn, int(list_id)) is not None,
    }


def dismissed(ctx, list_id: str, **_):
    _require(ctx.conn, int(list_id))
    trials = _rows(ctx, int(list_id), True)
    return {"trials": trials, "counts": {"trials": len(trials)}}


def dismiss(ctx, list_id: str, body=None, **_):
    _require(ctx.conn, int(list_id))
    ids = _ids(body)
    done = []
    for nct in ids:
        offered = [o for o in storage.list_found(ctx.conn, int(list_id)) if o["nct_id"] == nct]
        if offered:
            monitor.dismiss(ctx.conn, int(list_id), nct)
            done.append(nct)
    return {"dismissed": done, "undo_token": ",".join(done)}


def restore(ctx, list_id: str, body=None, **_):
    _require(ctx.conn, int(list_id))
    done = [n for n in _ids(body) if monitor.restore_match(ctx.conn, int(list_id), n)]
    return {"restored": done}


def undo(ctx, list_id: str, body=None, **_):
    """Undo a dismissal: restore exactly the trials its token names."""
    _require(ctx.conn, int(list_id))
    token = (body or {}).get("token")
    if not isinstance(token, str):
        raise ApiError(400, "invalid_request", "Send the undo token the dismissal returned.")
    return restore(ctx, list_id, {"nct_ids": [t for t in token.split(",") if t]})
