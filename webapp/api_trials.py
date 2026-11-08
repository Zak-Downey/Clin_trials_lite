"""A watched trial's changes."""

from __future__ import annotations

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
