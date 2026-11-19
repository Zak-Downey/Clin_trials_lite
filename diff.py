"""Comparing two monitored profiles.

Pure functions only: no storage, no network, no registry knowledge beyond two
named sets of field names: those that must never be reported as changed, and
those whose movement matters most to the team reading the page.
"""

from __future__ import annotations

EXCLUDED = ("lastUpdatePostDate", "resultsUrl")


SPLIT = ("interventions",)


def _distinct(names) -> list:
    """Each name once, in the order it first appears."""
    return list(dict.fromkeys(names or ()))


def split(previous, current) -> dict[str, list]:
    """What moved between two lists of names: added, removed and unchanged.

    Names compare as distinct, exact text: a name repeated counts once, and a
    renamed one is one removed and one added. Added and unchanged keep the
    current list's order; removed keeps the previous list's. An absent list is
    an empty one.
    """
    before, after = _distinct(previous), _distinct(current)
    had, has = set(before), set(after)
    return {
        "added": [name for name in after if name not in had],
        "removed": [name for name in before if name not in has],
        "unchanged": [name for name in after if name in had],
    }


def _comparable(value):
    """The form of a value that decides whether it moved.

    The registry's ordering of a list carries no meaning, so lists compare by
    membership: a reordered list is not a change. Sorting by text keeps values
    of mixed types (and Nones) comparable.
    """
    if isinstance(value, list):
        return sorted(map(repr, value))
    return value


def moved(field: str, previous, current) -> bool:
    """Whether a field's value moved: the one rule for detecting a change and for
    deciding whether a change already saved is still one.

    A field in SPLIT moved only when its split adds or removes a name.
    """
    if field in SPLIT:
        parts = split(previous, current)
        return bool(parts["added"] or parts["removed"])
    return _comparable(previous) != _comparable(current)


def stands(change: dict) -> bool:
    """Whether a change already saved is still a change.

    A change saved before a field joined SPLIT may add and remove nothing (an
    intervention named more or fewer times, nothing else): it is no longer one,
    and is read under the same rule detection now uses. Any other field's saved
    change stands as it was recorded.
    """
    if change["field"] in SPLIT:
        return moved(change["field"], change["previous"], change["current"])
    return True


def compare(previous: dict, current: dict) -> list[dict]:
    """The fields that moved between two profiles, in profile order.

    Each entry carries the field name and both values, so a caller can show the
    direction of a move without going back to storage.
    """
    return [
        {"field": field, "previous": previous.get(field), "current": value}
        for field, value in current.items()
        if field not in EXCLUDED and moved(field, previous.get(field), value)
    ]


HIGH_SIGNAL = (
    "overallStatus",
    "whyStopped",
    "primaryCompletionDate",
    "completionDate",
    "enrollment",
    "armGroups",
    "interventions",
    "hasResults",
    "primaryOutcomes",
    "phases",
    "eligibilityCriteria",
)


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


def high_signal(field: str) -> bool:
    """Whether this field's movement is the kind the team acts on."""
    return field in HIGH_SIGNAL


def fold_moves(changes, profile: dict | None = None) -> list[dict]:
    """Recorded changes as the moves that name them, each qualifier folded in.

    The counterpart of annotate for a caller holding changes rather than a whole
    profile: the same rule that a value and the registry's word for it are one
    fact, applied where there is no profile row to hang it on.

    A qualifier that moved beside its own value adds no move of its own. One
    that moved alone is reported under the value it qualifies -- "now Actual"
    names nothing by itself -- with that value read off the profile, where it
    still stands unchanged.

    Owned here, beside the two maps that decide it, so a field the registry
    starts qualifying is one edit rather than one per caller. Each move carries
    the change row it came from, so a caller adds its own facts without this
    module learning what they are.
    """
    profile = profile or {}
    moved = {change["field"]: change for change in changes}

    folded = []
    for field, change in moved.items():
        qualified = QUALIFIES.get(field)
        if qualified:
            if qualified in moved:
                continue
            standing = profile.get(qualified)
            folded.append(
                {
                    "field": qualified,
                    "previous": standing,
                    "current": standing,
                    "previous_qualifier": change["previous"],
                    "qualifier": change["current"],
                    "change": change,
                    "changes": [change],
                }
            )
            continue

        qualifier = QUALIFIED_BY.get(field)
        alongside = moved.get(qualifier) if qualifier else None
        stated = profile.get(qualifier) if qualifier else None
        folded.append(
            {
                "field": field,
                "previous": change["previous"],
                "current": change["current"],
                "previous_qualifier": alongside["previous"] if alongside else stated,
                "qualifier": alongside["current"] if alongside else stated,
                "change": change,
                "changes": [change, alongside] if alongside else [change],
            }
        )
    return folded


def by_signal(fields) -> list[str]:
    """Field names ordered high-signal first, each group keeping its own order.

    Owned here because HIGH_SIGNAL is: a caller showing only the first few of a
    long list must be able to trust that a slipped completion date is not the
    one it drops.
    """
    return sorted(fields, key=lambda f: not high_signal(f))


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
        if field is None or field in EXCLUDED:
            return None
        return latest.get(field)

    rows = []
    for field, value in profile.items():
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
                "previous": move["previous"] if move else (value if qualified_move else None),
                "qualifier": stated,
                "previous_qualifier": (
                    qualified_move["previous"] if qualified_move else stated
                ),
                "high_signal": high_signal(field),
                "synthetic": any(
                    m["synthetic"] for m in (move, qualified_move) if m
                ),
            }
        )
    return rows
