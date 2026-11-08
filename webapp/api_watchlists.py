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


def all_trials(ctx, list_id: str, **_):
    """Every trial in the watchlist: identity, registry status, review state (a separate
    fact), last successful check and whether the latest check failed."""
    _require(ctx.conn, int(list_id))
    queue = {e["nct_id"]: e for e in monitor.needs_review(ctx.conn, int(list_id))}
    trials = []
    for t in storage.list_trials(ctx.conn, int(list_id)):
        nct = t["nct_id"]
        profile = monitor.profile_of(ctx.conn, nct) or {}
        changes = storage.list_changes(ctx.conn, nct)
        if nct in queue:
            n = queue[nct]["change_count"]
            review = {"state": "unreviewed", "label": f"{n} change{'' if n == 1 else 's'}"}
        elif changes:
            review = {"state": "reviewed", "label": "Reviewed"}
        else:
            review = {"state": "none", "label": "No changes"}
        trials.append(
            {
                "nct_id": nct,
                "heading": profile.get("acronym") or profile.get("briefTitle") or nct,
                "phase": display.phase_label(profile.get("phases")),
                "sponsor": profile.get("leadSponsor"),
                "status": display.status_label(profile.get("overallStatus")),
                "review": review,
                "latest_change": local(max(c["detected_at"] for c in changes)) if changes else None,
                "last_checked": local(t["last_checked"]),
                "check_failed": {"at": local(t["check_failed_at"]), "kind": t["check_error_kind"]}
                if t["check_failed_at"] else None,
            }
        )
    return {"trials": trials, "counts": {"trials": len(trials)}}
