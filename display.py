"""Pure formatting helpers shared by the view layer.

Kept out of the Streamlit page so they can be tested without running the app.
"""

from __future__ import annotations

import datetime
import re

EMPTY = "—"

# Shown against anything the simulator caused, so nobody in a demo mistakes
# fabricated data for the registry's. The mark alone is used where a cell is
# too narrow to spell it out.
SYNTHETIC_MARK = "🧪"
SYNTHETIC = f"{SYNTHETIC_MARK} SYNTHETIC"


def label(key: str) -> str:
    """camelCase profile key -> readable label. primaryCompletionDate -> 'Primary completion date'."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key).capitalize()


def show(value) -> str:
    """Render a profile value, making emptiness explicit rather than blank.

    A blank cell is indistinguishable from a rendering fault, which matters
    most for a field like a reason for stopping that is normally absent.
    """
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else EMPTY
    if value is None or value == "":
        return EMPTY
    return str(value)


# Streamlit's own colour directives, so the highlight is markdown rather than
# injected HTML. Which of the two a move gets is decided in field_line.
HIGHLIGHT = "orange-background"
HIGHLIGHT_HIGH_SIGNAL = "red-background"

RESULTS_LINK = "View results on ClinicalTrials.gov"

# Marks what has moved since the analyst last said they had read it.
UNREVIEWED = "🔔"


def field_line(row: dict) -> str:
    """One marked-up profile row, as a single line of the card holding it.

    Label beside value rather than above it: the profile's vertical white was
    one Streamlit block per field, and a card only reads compactly if a field
    costs one line rather than two.

    Kept here rather than in the page so what a highlight looks like can be
    tested without running Streamlit. Dates are shown as they are: the
    direction of a move is the intelligence, and no arithmetic is done on it.
    """
    name = label(row["field"])

    if row["field"] == "resultsUrl" and row["value"]:
        value = f"[{RESULTS_LINK}]({row['value']})"
    else:
        value = show(row["value"])

    if not row["changed"]:
        return f"**{name}** · {value}"

    # The louder colour is reserved for a high-signal move, so a slipped
    # completion date does not look like a typo fix in the official title.
    colour = HIGHLIGHT_HIGH_SIGNAL if row["high_signal"] else HIGHLIGHT
    # The mark alone: a card is a third of the page wide.
    fake = f" {SYNTHETIC_MARK}" if row["synthetic"] else ""
    return (
        f":{colour}[**{name}**]{fake} · {value}  \n"
        f"&nbsp;&nbsp;&nbsp;&nbsp;:gray[_Previously {show(row['previous'])}_]"
    )


# --- the dossier
#
# The profile is 41 fields, which in one column is several screens of mostly
# white. Dealt into titled cards across the page, each card answering one
# question about the study, the whole profile fits on roughly one screen and a
# reader after the dates goes straight to the card called that.

# Where each profile field belongs. Ordered: the cards are dealt in this order
# every time, so the reader learns where to look rather than re-reading titles.
#
# This restates a grouping medical_affairs.profile already implies, and it does
# so on purpose: the order fields are gathered in is a question about the
# registry, while the order they are read in is a question about the page, and
# the two are free to disagree. A field added there and not here still appears,
# under OTHER.
CARDS = [
    ("Identity", ("nctId", "briefTitle", "officialTitle", "acronym", "orgStudyId",
                  "secondaryIds")),
    ("Sponsor", ("leadSponsor", "sponsorClass", "collaborators", "responsibleParty")),
    ("Status and dates", ("overallStatus", "whyStopped", "startDate", "startDateType",
                          "primaryCompletionDate", "primaryCompletionDateType",
                          "completionDate", "completionDateType", "studyFirstPostDate",
                          "resultsFirstPostDate", "lastUpdatePostDate")),
    ("Drugs and arms", ("interventions", "interventionTypes", "armGroups",
                        "drugMeshTerms")),
    ("Disease and eligibility", ("conditions", "conditionMeshTerms", "sex",
                                 "minimumAge")),
    ("Design and scale", ("studyType", "phases", "enrollment", "enrollmentType",
                          "allocation", "primaryPurpose", "masking")),
    ("Endpoints", ("primaryOutcomes", "primaryOutcomeTimeFrames",
                   "secondaryOutcomeCount")),
    ("Results", ("hasResults", "resultsUrl")),
]

# Where a field the grouping does not recognise goes. A field added to the
# monitored profile later must show up somewhere rather than silently
# disappearing off the page.
OTHER = "Other"


def group_fields(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Marked profile rows dealt into the cards, in the order the cards are read.

    A card with none of its fields present is left out, so a profile that
    stops carrying results does not leave a titled empty box behind.
    """
    remaining = {row["field"]: row for row in rows}

    cards = []
    for title, fields in CARDS:
        held = [remaining.pop(f) for f in fields if f in remaining]
        if held:
            cards.append((title, held))

    if remaining:
        cards.append((OTHER, list(remaining.values())))
    return cards


def card_title(title: str, rows: list[dict]) -> str:
    """A card's heading, carrying how much inside it is still unread.

    A card can be scanned past, so the count is what stops a change hiding in
    one the reader's eye skipped.
    """
    unreviewed = sum(1 for row in rows if row["changed"])
    bell = f" {UNREVIEWED}{unreviewed}" if unreviewed else ""
    return f"**{title.upper()}**{bell}"


def render_card(title: str, rows: list[dict]) -> str:
    """A whole card as the single markdown block the page renders.

    One block, not one per field: Streamlit puts a margin around every block it
    draws, so rendering a card field by field would reproduce the vertical
    white this layout exists to remove.
    """
    return "  \n".join([card_title(title, rows)] + [field_line(row) for row in rows])


# --- the study tables
#
# One line per trial, so every cell is a single short string. Pure functions
# over a row from monitor.watchlist, kept here so the table's wording can be
# tested without running Streamlit.
#
# Two tables are drawn from this: the watchlist, and the search results that
# fill it. They share the columns below so a result reads as the line it is
# about to become, rather than as a different view of the same study.

# How many field names one cell shows before the rest collapse into "+n more".
# Three fits the column at a normal window width; the names arrive high-signal
# first, so what falls under the fold is always the least urgent of them.
CHANGE_CAP = 3

# A momentJS pattern, applied client-side by the date column. The month is
# spelled out: an all-numeric date has to be decoded before it can be read, and
# a spelled month cannot be misread as a day.
DATE_FORMAT = "DD MMMM YYYY"

PHASE_NAMES = {"NA": "N/A", "EARLY_PHASE1": "Early Phase 1"}


def phase_label(phases) -> str:
    """Registry phase codes as the phases a reader knows. PHASE2 -> 'Phase 2'."""
    if not phases:
        return EMPTY
    return "/".join(
        PHASE_NAMES.get(p, str(p).replace("PHASE", "Phase ")) for p in phases
    )


def status_label(status) -> str:
    """A registry status code as a sentence. ACTIVE_NOT_RECRUITING -> readable."""
    if not status:
        return EMPTY
    return status.replace("_", " ").capitalize()


def changed_fields(row: dict, cap: int = CHANGE_CAP) -> str:
    """The names of the fields that last moved on a trial, for one table cell.

    Names only: the from-and-to values make a single row informative but a
    column of them unscannable, and they are one click away in the profile
    below. A trial that has never changed says so rather than rendering blank.

    An unreviewed change is prefixed with the bell, so "changed last Tuesday"
    and "changed and nobody has read it" stay distinguishable in one column;
    a simulated one carries the flask.
    """
    change = row["change"]
    if change is None:
        return EMPTY

    names = [label(f) for f in change["fields"]]
    shown = ", ".join(names[:cap])
    hidden = len(names) - cap
    if hidden > 0:
        shown += f" +{hidden} more"

    prefix = f"{UNREVIEWED} " if row["unreviewed"] else ""
    fake = f" {SYNTHETIC_MARK}" if change["synthetic"] else ""
    return f"{prefix}{shown}{fake}"


def changed_on(row: dict) -> datetime.date | None:
    """The date that change was detected, as a date so the column sorts by time.

    A column of formatted date strings sorts alphabetically, which puts April
    before September before anything at all in 2025. Date only, not time: the
    stored stamps record when somebody pressed Check, not when the sponsor
    edited the record, so a time would be false precision.
    """
    change = row["change"]
    return datetime.date.fromisoformat(change["at"][:10]) if change else None


def study_line(row: dict) -> dict:
    """What identifies one study, as the cells of its table line.

    The columns the watchlist and the search results have in common, in the
    order both read them: identity, then the study, then where it stands. Each
    table adds its own columns around these -- the watchlist what moved, the
    search nothing -- but neither restates them.
    """
    return {
        "NCT ID": row["nct_id"],
        "Sponsor": show(row["sponsor"]),
        "Official title": show(row["title"]),
        "Phase": phase_label(row["phases"]),
        "Conditions": show(row["conditions"]),
        "Interventions": show(row["interventions"]),
        "Trial status": status_label(row["status"]),
    }


# How wide each shared column is dealt. Named widths rather than Streamlit
# column objects, so this module stays runnable without Streamlit and both
# pages lay the same columns out the same way.
#
# The two reference columns are the ones given up when a table runs out of
# room: a drug list rarely moves and is one click away, whereas a cut-off
# "What changed" is the column the watchlist exists for. So the news gets the
# width and these truncate first.
COLUMN_WIDTHS = {
    "NCT ID": "small",
    "Official title": "large",
    "Phase": "small",
    "Conditions": "small",
    "Interventions": "small",
    "Trial status": "small",
}
