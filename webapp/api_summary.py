"""A watchlist's change summary for a period (the Summary tab, its text and its CSV)."""

from __future__ import annotations

import datetime

import briefing
import display
import monitor
import storage

from .errors import ApiError
from .times import local


def _date(query, key: str) -> datetime.date:
    values = query.get(key)
    try:
        return datetime.date.fromisoformat(values[0]) if values else None
    except ValueError:
        return None


def _span(start: datetime.date, end: datetime.date) -> str:
    """"2–8 Nov 2026", "28 Oct – 3 Nov 2026" or "8 Nov 2026"."""
    if start == end:
        return f"{start.day} {start:%b %Y}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{end.day} {end:%b %Y}"
    if start.year == end.year:
        return f"{start.day} {start:%b} – {end.day} {end:%b %Y}"
    return f"{start.day} {start:%b %Y} – {end.day} {end:%b %Y}"


def _period(query) -> tuple[str, datetime.date, datetime.date]:
    kind = (query.get("period") or ["week"])[0]
    today = _date(query, "today") or datetime.date.today()
    if kind in ("week", "month"):
        return (kind, *briefing.period_range(kind, today))
    if kind == "custom":
        start, end = _date(query, "from"), _date(query, "to")
        if start is None or end is None:
            raise ApiError(400, "invalid_request", "Choose both dates, as YYYY-MM-DD.")
        if start > end:
            raise ApiError(400, "invalid_request", "The From date must not be after the To date.")
        return kind, start, end
    raise ApiError(400, "invalid_request", "The period is week, month or custom.")


def _latest(entry: dict) -> str:
    """"Latest: completion date and enrolment updated." -- the newest check's fields."""
    newest = max(move["detected"] for move in entry["moves"])
    labels = []
    for move in entry["moves"]:
        if move["detected"] == newest and move["label"].lower() not in labels:
            labels.append(move["label"].lower())
    named = labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]
    return f"Latest: {named} updated."


def _move(move: dict) -> dict:
    return {
        "ids": move["ids"],
        "field": move["field"],
        "label": move["label"],
        "previous": display.show(move["previous"]),
        "current": display.show(move["current"]),
        "previous_qualifier": str(move["previous_qualifier"]).capitalize() if move["previous_qualifier"] else None,
        "qualifier": str(move["qualifier"]).capitalize() if move["qualifier"] else None,
        "registry_updated": move["registry_updated"],
        "reviewed": move["reviewed"],
        "simulated": move["synthetic"],
    }


def _trial(conn, entry: dict) -> dict:
    profile = monitor.profile_of(conn, entry["nct_id"]) or {}
    checks: dict[str, list[dict]] = {}
    for move in entry["moves"]:
        checks.setdefault(move["detected"], []).append(_move(move))
    # Newest check first, the order the summary is read in; within one check
    # the entry's own order (high-signal first) stands.
    ordered = sorted(checks.items(), key=lambda item: item[0], reverse=True)
    return {
        "nct_id": entry["nct_id"],
        "heading": profile.get("acronym") or profile.get("briefTitle") or entry["nct_id"],
        "url": entry["url"],
        "change_count": len(entry["moves"]),
        "check_count": len(ordered),
        "latest": _latest(entry),
        "simulated": entry["synthetic"],
        "checks": [{"detected_at": local(when), "changes": moves} for when, moves in ordered],
    }


def summary(ctx, list_id: str, query=None, **_):
    if storage.get_list(ctx.conn, int(list_id)) is None:
        raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")
    kind, start, end = _period(query or {})
    gathered = briefing.summarise(ctx.conn, int(list_id), start, end, zone=None)
    moves = [move for entry in gathered["entries"] for move in entry["moves"]]
    reviewed = sum(1 for move in moves if move["reviewed"])
    return {
        "period": {"kind": kind, "start": str(start), "end": str(end), "label": _span(start, end)},
        "zone": datetime.datetime.now().astimezone().tzname(),
        "counts": {
            "trials": len(gathered["entries"]),
            "field_changes": len(moves),
            "awaiting_review": len(moves) - reviewed,
            "reviewed": reviewed,
        },
        "trials": [_trial(ctx.conn, entry) for entry in gathered["entries"]],
        "text": briefing.as_text(gathered),
        "csv": briefing.as_csv(gathered),
        "filename": briefing.filename(gathered),
    }
