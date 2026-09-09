"""The change summary that leaves the tool.

An analyst's output is a briefing, not a dashboard: a line in an email, a row in
somebody else's tracker. Everything that line needs is already stored -- the
field, both its values, when the sponsor revised the record, when this tool
noticed, and where to read the study -- so this module gathers it over a chosen
range and hands it over in the two forms it leaves in: text to copy, and a CSV
to open in a spreadsheet.

Both forms are rendered from one gathered summary, so the file and the pasted
paragraph can never disagree about what happened.

Reviewed and unreviewed changes alike: a briefing covers what happened in a
window, not what is still unread. That is a different question from the one the
watchlist answers, which is why the review flag is read nowhere in here.

Nothing simulated is allowed out unmarked. A briefing is exactly the place where
fabricated data must not pass as real, so the mark travels with every move into
both forms rather than being drawn on the page around them.
"""

from __future__ import annotations

import csv
import datetime
import io
import re
import sqlite3

import diff
import display
import medical_affairs
import storage

# The ranges offered before the reader reaches for a calendar. Both end today:
# a briefing is written about what has happened, and a range running into next
# week would report the same thing while implying otherwise.
THIS_WEEK = "This week"
THIS_MONTH = "This month"
CUSTOM = "Custom range"
PRESETS = (THIS_WEEK, THIS_MONTH, CUSTOM)


def preset_range(name: str, today: datetime.date | None = None):
    """The dates a preset means, or None for the range the reader picks.

    Weeks run from Monday, which is the week a working Friday briefing covers.
    """
    day = today or datetime.date.today()
    if name == THIS_WEEK:
        return day - datetime.timedelta(days=day.weekday()), day
    if name == THIS_MONTH:
        return day.replace(day=1), day
    return None


# --- gathering


def _within(stamp: str, start: datetime.date, end: datetime.date) -> bool:
    """Whether a detection stamp falls inside the range, both days included.

    Compared by date rather than by moment: the reader chose two days, so a
    change detected at half past eleven at night on the closing day is inside
    the range they asked for.
    """
    return str(start) <= stamp[:10] <= str(end)


def _list_name(conn: sqlite3.Connection, list_id: int | None) -> str:
    """The list the briefing is about, by name -- it says so at the top."""
    if list_id is None:
        return "Everything monitored"
    row = storage.get_list(conn, list_id)
    return row["name"] if row else "Everything monitored"


def _profile_at(conn: sqlite3.Connection, nct_id: str, when: str) -> dict:
    """The trial's monitored profile as it stood when a change was detected.

    A check writes its snapshot and its change rows under one stamp, so this is
    the record the change was found in -- which is what dates the move by the
    sponsor's own revision rather than by whatever the trial says today.
    """
    snapshot = storage.snapshot_at(conn, nct_id, when)
    return medical_affairs.profile(snapshot["record"]) if snapshot else {}


def _move(folded: dict, registry_updated) -> dict:
    """One folded movement, carrying everything a briefing line names.

    What moved and what it moved from is diff's answer; when it happened, what
    it is called and how loudly it should be read are this module's.
    """
    change = folded["change"]
    field = folded["field"]
    return {
        **{key: value for key, value in folded.items() if key != "change"},
        "label": display.label(field),
        "registry_updated": registry_updated,
        "detected": change["detected_at"],
        "synthetic": change["synthetic"],
        "high_signal": diff.high_signal(field),
    }


def _detection(conn: sqlite3.Connection, nct_id: str, when: str, changes: list[dict]) -> list[dict]:
    """What one check found on one trial, as the moves a briefing reports.

    The record as it stood at that moment is read once: it dates the moves by
    the sponsor's own revision, and it is where a value whose qualifier alone
    moved is read from.
    """
    profile = _profile_at(conn, nct_id, when)
    registry_updated = profile.get("lastUpdatePostDate")
    return [_move(folded, registry_updated) for folded in diff.fold_moves(changes, profile)]


def _title(conn: sqlite3.Connection, nct_id: str) -> str | None:
    """What the study is called, as its newest stored record has it."""
    snapshot = storage.latest_snapshot(conn, nct_id)
    if snapshot is None:
        return None
    profile = medical_affairs.profile(snapshot["record"])
    return profile.get("officialTitle") or profile.get("briefTitle")


def summarise(
    conn: sqlite3.Connection,
    list_id: int | None,
    start: datetime.date,
    end: datetime.date,
) -> dict:
    """Everything one list moved by, over a range of days.

    One entry per trial, however many checks its moves are spread across, with
    the fields high-signal first inside it: a briefing that leads on a corrected
    typo has buried the completion date that slipped underneath it.

    Trials are ordered by their most recent move, so the newest news opens the
    briefing.
    """
    watched = {row["nct_id"] for row in storage.list_trials(conn, list_id)}
    changes = [
        change
        for change in storage.list_changes(conn)
        if change["nct_id"] in watched and _within(change["detected_at"], start, end)
    ]

    # Changes arrive newest first, so grouping preserves that order and the
    # entries below are already in the order they are read.
    detections: dict[tuple[str, str], list[dict]] = {}
    for change in changes:
        detections.setdefault((change["nct_id"], change["detected_at"]), []).append(change)

    moves: dict[str, list[dict]] = {}
    for (nct_id, when), found in detections.items():
        moves.setdefault(nct_id, []).extend(_detection(conn, nct_id, when, found))

    entries = [
        {
            "nct_id": nct_id,
            "title": _title(conn, nct_id),
            "url": f"{display.STUDY_URL}/{nct_id}",
            "synthetic": any(move["synthetic"] for move in found),
            # Stable, so within the high-signal group the newest check still
            # comes first.
            "moves": sorted(found, key=lambda move: not move["high_signal"]),
        }
        for nct_id, found in moves.items()
    ]

    return {
        "list_name": _list_name(conn, list_id),
        "start": start,
        "end": end,
        "entries": entries,
        "moves": sum(len(entry["moves"]) for entry in entries),
    }


# --- the two forms

# The word marking a fabricated move in a spreadsheet, where an emoji is not
# something a filter or a formula can be written against. The app's own word,
# so a row of the file and a line of the page are saying the same thing.
SYNTHETIC = display.SYNTHETIC.removeprefix(display.SYNTHETIC_MARK).strip()

COLUMNS = (
    "List",
    "NCT ID",
    "Title",
    "Field",
    "Previous",
    "Current",
    "Registry updated",
    "Detected",
    "Synthetic",
    "Registry record",
)


def _value(move: dict, side: str) -> str:
    """One side of a move, as the single line a briefing gives it.

    The qualifier travels with the value it qualifies: a completion date going
    from estimated to actual is the whole of the news, and neither half of that
    states it alone.
    """
    qualifier = move["previous_qualifier"] if side == "previous" else move["qualifier"]
    return display.collapse(display.qualified(move[side], qualifier)) or display.EMPTY


def _nothing(summary: dict) -> str:
    """What an empty range says.

    Said rather than handed over as an empty file: a briefing nobody can tell
    apart from a broken export is worse than no briefing.
    """
    return (
        f"No changes were detected in “{summary['list_name']}” between "
        f"{display.long_date(summary['start'])} and {display.long_date(summary['end'])}."
    )


def _heading(summary: dict) -> str:
    return (
        f"{summary['list_name']} — changes detected "
        f"{display.long_date(summary['start'])} to {display.long_date(summary['end'])}"
    )


def _counted(summary: dict) -> str:
    trials = len(summary["entries"])
    moves = summary["moves"]
    return (
        f"{trials} trial{'' if trials == 1 else 's'}, "
        f"{moves} change{'' if moves == 1 else 's'}."
    )


def as_text(summary: dict) -> str:
    """The briefing as text, to be pasted into an email or onto a slide.

    Plain lines rather than markup: it is going somewhere this tool does not
    render, so what it looks like here is what it looks like there.
    """
    lines = [_heading(summary)]
    if not summary["entries"]:
        return "\n\n".join([lines[0], _nothing(summary)])

    lines.append(_counted(summary))
    for entry in summary["entries"]:
        lines.append("")
        lines.append(f"{entry['nct_id']} — {display.show(entry['title'])}")
        lines.append(entry["url"])
        for move in entry["moves"]:
            mark = f" {display.SYNTHETIC}" if move["synthetic"] else ""
            lines.append(
                f"- {move['label']}: {_value(move, 'previous')} → {_value(move, 'current')}"
                # Dashed off rather than bracketed: a value carrying the
                # registry's "(Actual)" would otherwise sit inside a second set
                # of brackets and read as one parenthesis.
                f" — registry updated {display.long_date(move['registry_updated'])}, "
                f"detected {display.long_date(move['detected'])}{mark}"
            )
    return "\n".join(lines)


def as_csv(summary: dict) -> str | None:
    """The same moves as a spreadsheet, one row each -- or None if there are none.

    None rather than a file of headings: a range with nothing in it is answered
    in words on the page, and an empty download is a thing to be puzzled over.

    Dates are given as the registry gives them, so a column of them sorts.
    """
    if not summary["entries"]:
        return None

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    for entry in summary["entries"]:
        for move in entry["moves"]:
            writer.writerow(
                [
                    summary["list_name"],
                    entry["nct_id"],
                    display.collapse(display.show(entry["title"])),
                    move["label"],
                    _value(move, "previous"),
                    _value(move, "current"),
                    move["registry_updated"] or "",
                    move["detected"][:10],
                    SYNTHETIC if move["synthetic"] else "",
                    entry["url"],
                ]
            )
    return out.getvalue()


def filename(summary: dict) -> str:
    """What the downloaded file is called: which list, and which days.

    Named rather than left as the browser's default, because the file lands in
    somebody's downloads folder beside last month's and has to be told apart.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", summary["list_name"].lower()).strip("-")
    return f"{slug or 'watchlist'}-changes-{summary['start']}-to-{summary['end']}.csv"
