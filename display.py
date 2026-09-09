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

# The eligibility criteria: the inclusion and exclusion list deciding who can
# enter the study. Forty lines of bullets in a card a third of the page wide,
# so the card carries an excerpt and the exact wording stays one registry link
# away -- and an amendment is *said* rather than printed twice over, because a
# full before-and-after would swamp the card and every other change beside it.
CRITERIA = "eligibilityCriteria"
CRITERIA_LINK = "Full criteria"
AMENDED = "Amended — the wording is on the registry"

# Where a study is read in full. Stated here rather than reached for in
# medical_affairs, which owns the same root for the results link: this module
# formats and nothing else, and importing the registry client to obtain one
# string would put the network client behind every page that renders a label.
STUDY_URL = "https://clinicaltrials.gov/study"

# The markers the registry lists criteria with, which carry no meaning once the
# list is one line.
BULLETS = ("*", "-", "•")

# How many characters of the criteria the excerpt carries. Enough to tell which population
# the study is in, short enough that the field costs a line like any other.
EXCERPT_CHARS = 180


def excerpt(text, limit: int = EXCERPT_CHARS) -> str:
    """Long free text as one short line, ending in an ellipsis when it is cut.

    The registry's line breaks collapse to single spaces and its bullet markers
    are dropped: a card is rendered as one markdown block, and a bulleted list
    dropped into it would either break the block apart or be read as emphasis.
    """
    words = [w for w in str(text).split() if w not in BULLETS] if text else []
    collapsed = " ".join(words)
    if not collapsed:
        return EMPTY
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip(" ,;:-*") + "…"


def _qualified(value, qualifier) -> str:
    """A value beside the registry's word for it: "2024-04-18 (Actual)".

    Read together because they are one fact: a date going from estimated to
    actual is the most informative thing that can happen to it, and neither
    half of that says it alone.
    """
    shown = show(value)
    return f"{shown} ({str(qualifier).capitalize()})" if qualifier else shown


def field_line(row: dict, nct_id: str | None = None) -> str:
    """One marked-up profile row, as a single line of the card holding it.

    Label beside value rather than above it: the profile's vertical white was
    one Streamlit block per field, and a card only reads compactly if a field
    costs one line rather than two.

    Kept here rather than in the page so what a highlight looks like can be
    tested without running Streamlit. Dates are shown as they are: the
    direction of a move is the intelligence, and no arithmetic is done on it.

    The trial is named only so the criteria can link out to their full wording;
    every other field renders without it.
    """
    name = label(row["field"])
    criteria = row["field"] == CRITERIA

    if criteria:
        value = excerpt(row["value"])
        # No link off an empty field: there is no wording on the registry to
        # follow it to.
        if nct_id and row["value"]:
            value += f" [{CRITERIA_LINK}]({STUDY_URL}/{nct_id})"
    elif row["field"] == "resultsUrl" and row["value"]:
        value = f"[{RESULTS_LINK}]({row['value']})"
    else:
        value = _qualified(row["value"], row.get("qualifier"))

    if not row["changed"]:
        return f"**{name}** · {value}"

    # The louder colour is reserved for a high-signal move, so a slipped
    # completion date does not look like a typo fix in the official title.
    colour = HIGHLIGHT_HIGH_SIGNAL if row["high_signal"] else HIGHLIGHT
    # The mark alone: a card is a third of the page wide.
    fake = f" {SYNTHETIC_MARK}" if row["synthetic"] else ""
    # The criteria state that they moved rather than repeating themselves at
    # length; every other field is short enough to show what it moved from.
    was = (
        AMENDED
        if criteria
        else f"Previously {_qualified(row['previous'], row.get('previous_qualifier'))}"
    )
    return (
        f":{colour}[**{name}**]{fake} · {value}  \n"
        f"&nbsp;&nbsp;&nbsp;&nbsp;:gray[_{was}_]"
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
# A field the registry qualifies as estimated or actual is listed once, under
# the value's own name: the marked-up rows carry the qualifier folded into the
# value, so a qualifier never arrives as a field of its own to be dealt.
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
    ("Status and dates", ("overallStatus", "whyStopped", "startDate",
                          "primaryCompletionDate", "completionDate",
                          "studyFirstPostDate", "resultsFirstPostDate",
                          "lastUpdatePostDate")),
    ("Drugs and arms", ("interventions", "interventionTypes", "armGroups",
                        "drugMeshTerms")),
    ("Disease and eligibility", ("conditions", "conditionMeshTerms", "sex",
                                 "minimumAge", "eligibilityCriteria")),
    ("Design and scale", ("studyType", "phases", "enrollment", "allocation",
                          "primaryPurpose", "masking")),
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


def render_card(title: str, rows: list[dict], nct_id: str | None = None) -> str:
    """A whole card as the single markdown block the page renders.

    One block, not one per field: Streamlit puts a margin around every block it
    draws, so rendering a card field by field would reproduce the vertical
    white this layout exists to remove.
    """
    return "  \n".join(
        [card_title(title, rows)] + [field_line(row, nct_id) for row in rows]
    )


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
    """The names of the fields outstanding on a trial, for one table cell.

    What is outstanding, not what moved most recently -- monitor.last_change
    decides which those are, and they can span several checks. Names only: the
    from-and-to values make a single row informative but a column of them
    unscannable, and they are one click away in the profile below. A trial that
    has never changed says so rather than rendering blank.

    A row with anything unread is prefixed with the bell, so "this trial has
    changed" and "nobody has read it" stay distinguishable in one column; a
    simulated change carries the flask.
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


def _as_date(stamp) -> datetime.date | None:
    """A stored stamp as a date, so a column of them sorts by time.

    A column of formatted date strings sorts alphabetically, which puts April
    before September before anything at all in 2025. Date only, not time: the
    stamps record a day's business, so a time would be false precision.
    """
    return datetime.date.fromisoformat(stamp[:10]) if stamp else None


def detected_on(row: dict) -> datetime.date | None:
    """The day this tool noticed the change -- the day somebody pressed Check."""
    change = row["change"]
    return _as_date(change["at"]) if change else None


def registry_updated(row: dict) -> datetime.date | None:
    """The day the sponsor revised the record, as the registry states it.

    Read beside the detected date, and only meaningful beside it: a watchlist
    checked weekly can show a fortnight-old revision as though it landed this
    morning, and the pair is what tells those two apart. A trial that has never
    changed has no revision to date, so it renders empty rather than dating the
    record's own history.

    It is the registry's newest stamp, not a stamp stored per change: nothing
    records which revision each field moved in. So on a trial with older moves
    still outstanding this dates the latest revision rather than each of them,
    which is why a check that changes nothing monitored leaves the stored
    record alone rather than advancing the stamp past the news beside it.
    """
    return _as_date(row["registry_updated"]) if row["change"] else None


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
