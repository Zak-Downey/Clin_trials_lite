"""A watched trial's changes."""

from __future__ import annotations

import medical_affairs
import storage

from .errors import ApiError
from .times import local


def changes(ctx, nct_id: str, **_):
    with ctx.lock:
        if storage.get_trial(ctx.conn, nct_id) is None:
            raise ApiError(404, "trial_not_found", f"{nct_id} is not being monitored.")
        out = []
        for change in storage.list_changes(ctx.conn, nct_id):
            snapshot = storage.snapshot_at(ctx.conn, nct_id, change["detected_at"])
            updated = medical_affairs.profile(snapshot["record"])["lastUpdatePostDate"] if snapshot else None
            out.append(
                {
                    "id": change["id"],
                    "field": change["field"],
                    "check": change["detected_at"],
                    "previous": change["previous"],
                    "current": change["current"],
                    "registry_updated": updated,
                    "detected_at": local(change["detected_at"]),
                    "reviewed": change["reviewed"],
                    "synthetic": change["synthetic"],
                }
            )
    return {"changes": out}
