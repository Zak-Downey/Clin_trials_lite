"""Comparing two monitored profiles.

Pure functions only: no storage, no network, no registry knowledge beyond the
names of the fields that must never be reported.
"""

from __future__ import annotations

# Two fields are deliberately never reported as changed:
#   lastUpdatePostDate -- the registry's own stamp, which moves by definition
#     whenever anything else does, so alerting on it is circular.
#   resultsUrl -- derived from hasResults, so alerting on it duplicates that.
EXCLUDED = ("lastUpdatePostDate", "resultsUrl")


def _comparable(value):
    """The form of a value that decides whether it moved.

    The registry's ordering of a list carries no meaning, so lists compare by
    membership: a reordered list is not a change. Sorting by text keeps values
    of mixed types (and Nones) comparable.
    """
    if isinstance(value, list):
        return sorted(map(repr, value))
    return value


def compare(previous: dict, current: dict) -> list[dict]:
    """The fields that moved between two profiles, in profile order.

    Each entry carries the field name and both values, so a caller can show the
    direction of a move without going back to storage.
    """
    return [
        {"field": field, "previous": previous.get(field), "current": value}
        for field, value in current.items()
        if field not in EXCLUDED
        and _comparable(previous.get(field)) != _comparable(value)
    ]
