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
    # A moved endpoint, a trial that changed phase, and an amended eligible
    # population are each read as competitor intelligence ahead of an edit to
    # the intervention wording, so none of them is what the watchlist's
    # overflow drops.
    "primaryOutcomes",
    "phases",
    "eligibilityCriteria",
)


# A value and the registry's word for whether it is estimated or actual. The
# pair is one fact: a primary completion date going from estimated to actual is
# the single most informative thing that can happen to that field, and reported
# as a date move plus an unrelated type move it reads as neither. So the
# qualifier is folded into the value it qualifies wherever a change is named.
QUALIFIED_BY = {
    "startDate": "startDateType",
    "primaryCompletionDate": "primaryCompletionDateType",
    "completionDate": "completionDateType",
    "enrollment": "enrollmentType",
}
QUALIFIES = {qualifier: value for value, qualifier in QUALIFIED_BY.items()}


def fold_qualifiers(fields) -> list[str]:
    """Field names with each qualifier named as the value it qualifies.

    Order is kept, and a qualifier that moved alongside its own value adds no
    second name: the two are one entry.
    """
    return list(dict.fromkeys(QUALIFIES.get(field, field) for field in fields))


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

    A field the registry qualifies as estimated or actual is one row, carrying
    the qualifier and the one it moved from, rather than two rows of which the
    second explains nothing on its own.
    """
    latest = _latest_unreviewed(changes)

    def moved(field):
        # A field that is never reported as changed is never marked as one,
        # whatever happens to be recorded against it.
        if field is None or field in EXCLUDED:
            return None
        return latest.get(field)

    rows = []
    for field, value in profile.items():
        # A qualifier has no row of its own: it is folded into the value it
        # qualifies, which is the row above it in profile order.
        if field in QUALIFIES:
            continue

        qualifier = QUALIFIED_BY.get(field)
        stated = profile.get(qualifier) if qualifier else None
        move, qualified_move = moved(field), moved(qualifier)

        rows.append(
            {
                "field": field,
                "value": value,
                "changed": bool(move or qualified_move),
                # What the field moved from, which for a value whose qualifier
                # alone moved is the value it still holds: the news there is
                # the qualifier, and the value is the context for it.
                "previous": move["previous"] if move else (value if qualified_move else None),
                "qualifier": stated,
                "previous_qualifier": (
                    qualified_move["previous"] if qualified_move else stated
                ),
                "high_signal": field in HIGH_SIGNAL,
                "synthetic": any(
                    m["synthetic"] for m in (move, qualified_move) if m
                ),
            }
        )
    return rows
