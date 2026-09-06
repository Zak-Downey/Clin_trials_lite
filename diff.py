"""Comparing two monitored profiles.

Pure functions only: no storage, no network, no registry knowledge beyond two
named sets of field names: those that must never be reported as changed, and
those whose movement matters most to the team reading the page.
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


# The fields a medical affairs team acts on. A slipped completion date and a
# typo fix in the official title must not look alike, so these are marked for
# greater prominence when they move.
HIGH_SIGNAL = (
    "overallStatus",
    "whyStopped",
    "primaryCompletionDate",
    "completionDate",
    "enrollment",
    "armGroups",
    "interventions",
    "hasResults",
)


def by_signal(fields) -> list[str]:
    """Field names ordered high-signal first, each group keeping its own order.

    Owned here because HIGH_SIGNAL is: a caller showing only the first few of a
    long list must be able to trust that a slipped completion date is not the
    one it drops.
    """
    return sorted(fields, key=lambda f: f not in HIGH_SIGNAL)


def _latest_unreviewed(changes: list[dict]) -> dict[str, dict]:
    """The latest change per field that has not yet been reviewed.

    A change the analyst has already read is not news, so it stops being
    marked. The row itself stays in storage; only the marking is dropped.

    A field that moved more than once resolves to its immediately preceding
    value, not the value it started from: chaining back through a field's whole
    history is a later feature.

    Changes are expected newest first, as storage returns them. Detection times
    are only second-precise, so two moves recorded in the same second cannot be
    told apart by time: the first seen wins, which under that order is the
    later one.
    """
    latest: dict[str, dict] = {}
    for change in changes:
        if change["reviewed"]:
            continue
        seen = latest.get(change["field"])
        if seen is None or change["detected_at"] > seen["detected_at"]:
            latest[change["field"]] = change
    return latest


def annotate(profile: dict, changes: list[dict]) -> list[dict]:
    """The whole profile as rows, each marked with what moved.

    Every field is returned, changed or not: a move is read in the context of
    the study rather than in isolation. A row carries the value it moved from,
    whether the field is high-signal, and whether the move was simulated.

    A row is "changed" when it carries a move not yet reviewed, so a highlight
    means "new since you last looked" rather than "moved at some point": a
    reviewed move leaves its row plain, though the record of it remains.
    """
    latest = _latest_unreviewed(changes)
    rows = []
    for field, value in profile.items():
        # A field that is never reported as changed is never marked as one,
        # whatever happens to be recorded against it.
        moved = None if field in EXCLUDED else latest.get(field)
        rows.append(
            {
                "field": field,
                "value": value,
                "changed": moved is not None,
                "previous": moved["previous"] if moved else None,
                "high_signal": field in HIGH_SIGNAL,
                "synthetic": bool(moved and moved["synthetic"]),
            }
        )
    return rows
