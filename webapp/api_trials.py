"""A watched trial's changes."""

from __future__ import annotations

import display
import monitor
import storage

from .errors import ApiError
from .times import local


def changes(ctx, nct_id: str, **_):
    """The trial's moves, newest first. A move is a value with its qualifier folded in,
    and carries the IDs of every change row it folds (the same unit the queue counts)."""
    if storage.get_trial(ctx.conn, nct_id) is None:
        raise ApiError(404, "trial_not_found", f"{nct_id} is not being monitored.")
    out = [
        {
            "ids": move["ids"],
            "field": move["field"],
            "check": move["check"],
            "previous": move["previous"],
            "current": move["current"],
            "previous_qualifier": move["previous_qualifier"],
            "qualifier": move["qualifier"],
            "registry_updated": move["registry_updated"],
            "detected_at": local(move["detected_at"]),
            "reviewed": move["reviewed"],
            "synthetic": move["synthetic"],
        }
        for move in monitor.history(ctx.conn, nct_id)
    ]
    return {"changes": out}


def _word(qualifier) -> str | None:
    """The registry's word for a value ("Actual"), shown beside it."""
    return str(qualifier).capitalize() if qualifier else None


def _event(event: dict) -> dict:
    return {
        "id": event["id"],
        "nct_id": event["nct_id"],
        "reviewed_at": local(event["reviewed_at"]),
        "change_ids": event["change_ids"],
        "undone_at": local(event["undone_at"]),
    }


def _require(ctx, nct_id: str) -> str:
    nct = nct_id.upper()
    if storage.get_trial(ctx.conn, nct) is None:
        raise ApiError(404, "trial_not_found", f"{nct} is not being monitored.")
    return nct


def trial(ctx, nct_id: str, **_):
    """The trial page: header facts, the watchlists holding it, and its unreviewed
    changes grouped by the check that found them (newest check first)."""
    nct = _require(ctx, nct_id)
    profile = monitor.profile_of(ctx.conn, nct) or {}
    groups: dict[str, dict] = {}
    for move in monitor.history(ctx.conn, nct):
        if move["reviewed"]:
            continue
        group = groups.setdefault(
            move["check"],
            {
                "check": move["check"],
                "detected_at": local(move["detected_at"]),
                "registry_updated": display.long_date(move["registry_updated"])
                if move["registry_updated"] else None,
                "changes": [],
            },
        )
        group["changes"].append(
            {
                "ids": move["ids"],
                "field": move["field"],
                "label": display.label(move["field"]),
                "previous": display.show(move["previous"]),
                "current": display.show(move["current"]),
                "previous_qualifier": _word(move["previous_qualifier"]),
                "qualifier": _word(move["qualifier"]),
                "simulated": move["synthetic"],
            }
        )
    ordered = sorted(groups.values(), key=lambda g: g["check"], reverse=True)
    return {
        "nct_id": nct,
        "heading": profile.get("acronym") or profile.get("briefTitle") or nct,
        "official_title": profile.get("officialTitle"),
        "phase": display.phase_label(profile.get("phases")),
        "sponsor": profile.get("leadSponsor"),
        "status": display.status_label(profile.get("overallStatus")),
        "registry_url": f"{display.STUDY_URL}/{nct}",
        "watchlists": [
            {"id": row["id"], "name": row["name"]} for row in storage.lists_holding(ctx.conn, nct)
        ],
        "groups": ordered,
        "change_count": sum(len(g["changes"]) for g in ordered),
        "simulated": any(c["simulated"] for g in ordered for c in g["changes"]),
    }


def review(ctx, nct_id: str, body=None, **_):
    """Mark exactly the change IDs sent as reviewed; the review applies to the trial everywhere."""
    nct = _require(ctx, nct_id)
    ids = (body or {}).get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
        raise ApiError(400, "invalid_request", "Send the IDs of the changes shown, as a list of numbers.")
    event = monitor.review_changes(ctx.conn, nct, ids)
    return {
        "event": _event(event) if event else None,
        "marked": event["change_ids"] if event else [],
        "unreviewed_count": storage.count_unreviewed(ctx.conn, nct),
    }


def undo_review(ctx, event_id: str, **_):
    """Return exactly the changes a review event marked to unreviewed."""
    existing = storage.get_review_event(ctx.conn, int(event_id))
    if existing is None:
        raise ApiError(404, "review_not_found", f"There is no review {event_id}.")
    event = monitor.undo_review(ctx.conn, int(event_id))
    if event is None:
        raise ApiError(409, "already_undone", "That review was already undone.")
    return {
        "event": _event(event),
        "restored": event["change_ids"],
        "unreviewed_count": storage.count_unreviewed(ctx.conn, event["nct_id"]),
    }
