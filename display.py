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


def collapse(text) -> str:
    """Free text as a single line, or "" if there is nothing in it.

    The registry writes criteria as a bulleted block; a line of a briefing and a
    cell of a CSV are both one line, so the breaks close up and the markers go.
    """
    words = [w for w in str(text).split() if w not in BULLETS] if text else []
    return " ".join(words)


def excerpt(text, limit: int = EXCERPT_CHARS) -> str:
    """Long free text as one short line, ending in an ellipsis when it is cut.

    The registry's line breaks collapse to single spaces and its bullet markers
    are dropped: a card is rendered as one markdown block, and a bulleted list
    dropped into it would either break the block apart or be read as emphasis.
    """
    collapsed = collapse(text)
    if not collapsed:
        return EMPTY
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip(" ,;:-*") + "…"


def qualified(value, qualifier) -> str:
    """A value beside the registry's word for it: "2024-04-18 (Actual)".

    Read together because they are one fact: a date going from estimated to
    actual is the most informative thing that can happen to it, and neither
    half of that says it alone.
    """
    shown = show(value)
    return f"{shown} ({str(qualifier).capitalize()})" if qualifier else shown


def long_date(value) -> str:
    """A stored stamp as a reader's date: "2026-03-01" -> "1 March 2026".

    The month is spelled out for the same reason the table spells it: a briefing
    is read by whoever it was pasted to, and 03/01 is a different day to them.
    A registry date stating only a month, and anything else unparseable, is
    passed through as it stands rather than guessed at.
    """
    if not value:
        return EMPTY
    text = str(value)[:10]
    try:
        day = datetime.date.fromisoformat(text)
    except ValueError:
        return text
    return f"{day.day} {day:%B %Y}"


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
        value = qualified(row["value"], row.get("qualifier"))

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
        else f"Previously {qualified(row['previous'], row.get('previous_qualifier'))}"
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

# How a date box is typed into. Streamlit's date_input takes only a handful of
# orders and the table's spelled-out month is not one of them, so this is the
# nearest unambiguous form -- day first, the way it is written here.
INPUT_DATE_FORMAT = "DD/MM/YYYY"

PHASE_NAMES = {"NA": "N/A", "EARLY_PHASE1": "Early Phase 1"}


def phase_label(phases) -> str:
    """Registry phase codes as the phases a reader knows. PHASE2 -> 'Phase 2'."""
    if not phases:
        return EMPTY
    return "/".join(
        PHASE_NAMES.get(p, str(p).replace("PHASE", "Phase ")) for p in phases
    )


# What each axis of a search is called, in the order it is typed and read back.
# One place, read by both the form that asks and the line that says what a list
# is watching for, so the screen an analyst types into cannot come to disagree
# with the screen that tells them what they typed. The axes themselves are
# monitor's list; these are the words.
AXIS_NAMES = {
    "cond": "Condition",
    "intr": "Intervention",
    "spons": "Sponsor",
    "phases": "Phase",
    "sponsor_types": "Sponsor type",
    "statuses": "Status",
    "started_from": "Started on or after",
    "started_to": "Started on or before",
}

# How a coded axis is turned into words. An axis absent here is free text and
# is printed as typed.
AXIS_FORMATS = {
    "phases": lambda codes: phase_label(codes),
    "sponsor_types": lambda codes: sponsor_type_label(codes),
    "statuses": lambda codes: statuses_label(codes),
}

# Axes whose value already contains its own label: "Phase 3" needs no "Phase"
# in front of it, and the date window reads as a sentence of its own.
SELF_NAMING = ("phases", "started_from", "started_to")

# The order the axes are read back in, which is the order they are typed.
READ_BACK_ORDER = ("cond", "intr", "spons", "phases", "sponsor_types", "statuses")

# The registry's sponsor classes as the kinds of organisation they stand for.
#
# INDUSTRY is the commercial sponsors, and it is the lead sponsor's class only:
# a company funding somebody else's trial is a *collaborator* on it and is
# classed wherever the lead sponsor sits, which for an academic centre is
# OTHER. So OTHER is not "the ones that are not companies" and must not be
# labelled as though it were -- it is a mixed bucket, and saying so is the
# difference between a filter the analyst can trust and one that quietly drops
# a third of the commercial activity in their indication.
SPONSOR_TYPE_NAMES = {
    "INDUSTRY": "Industry",
    "OTHER": "Other (incl. academic)",
    "NIH": "NIH",
    "FED": "US federal",
    "OTHER_GOV": "Other government",
    "NETWORK": "Network",
    "INDIV": "Individual",
}

# The separator between codes of one axis, owned here so the three code axes
# cannot come to disagree about it.
CODES_JOIN = "/"


def _codes_label(codes, names: dict | None = None) -> str:
    """Several registry codes of one axis, as the words a reader knows."""
    if not codes:
        return EMPTY
    named = names or {}
    return CODES_JOIN.join(named.get(c, humanise(c)) for c in codes)


def sponsor_type_label(classes) -> str:
    """Registry sponsor classes as the kinds of organisation a reader knows."""
    return _codes_label(classes, SPONSOR_TYPE_NAMES)


def statuses_label(statuses) -> str:
    """Several registry statuses, as one phrase. The plural of status_label."""
    return _codes_label(statuses)


def started_label(started_from: str, started_to: str) -> str:
    """A start-date window as the sentence an analyst would say it in.

    Empty when neither end is set, rather than the EMPTY dash the other labels
    use: this one is a clause in a longer line, and an unset window should drop
    out of that line altogether rather than appear in it as a blank.

    Both bounds are inclusive, and said so: "on or after" rather than "since",
    because a window ending on the last of the month must not read as though it
    stopped the day before.
    """
    start, end = (started_from or "").strip(), (started_to or "").strip()
    if start and end:
        return f"started {long_date(start)} to {long_date(end)}"
    if start:
        return f"started on or after {long_date(start)}"
    if end:
        return f"started on or before {long_date(end)}"
    return ""


def search_line(query: dict | None) -> str:
    """What a list is watching for, as one line under its name.

    Named axis by axis rather than as a query string: the analyst has to be
    able to tell at a glance whether the list is still watching for the right
    thing, and "multiple myeloma" alone does not say which box it was typed in.

    Read with `.get`, because a search stored before an axis existed simply has
    no key for it and still has to render as the search it was.
    """
    if not query:
        return EMPTY
    parts = []
    for key in READ_BACK_ORDER:
        value = query.get(key)
        if not value:
            continue
        shown = AXIS_FORMATS[key](value) if key in AXIS_FORMATS else value
        # Named unless the value names itself. A bare "Network" or "Unknown"
        # does not say which box it was typed in, which is the whole reason
        # this line is built axis by axis rather than as a query string.
        parts.append(shown if key in SELF_NAMING else f"{AXIS_NAMES[key]} {shown}")
    window = started_label(query.get("started_from", ""), query.get("started_to", ""))
    if window:
        parts.append(window)
    return " · ".join(parts) or EMPTY


def humanise(code) -> str:
    """A registry code as a readable word. ACTIVE_NOT_RECRUITING -> readable.

    The fallback for every code axis: enough for a code whose words are its own
    meaning, and the reason a code the registry adds tomorrow still renders.
    """
    return str(code).replace("_", " ").capitalize()


def status_label(status) -> str:
    """A registry status code as a sentence."""
    if not status:
        return EMPTY
    return humanise(status)


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
