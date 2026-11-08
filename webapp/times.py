"""Stored UTC stamps as the machine's local time, with the zone named."""

from __future__ import annotations

import datetime


def local(stamp: str | None) -> dict | None:
    """{"iso": local time with its offset, "zone": e.g. "EST"}, or None."""
    if not stamp:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    here = parsed.astimezone()
    return {"iso": here.isoformat(timespec="seconds"), "zone": here.tzname()}
