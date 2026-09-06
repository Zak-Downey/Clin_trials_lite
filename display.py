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
# injected HTML. High-signal moves get the louder colour and a heading, so a
# slipped completion date does not look like a typo fix in the official title.
HIGHLIGHT = "orange-background"
HIGHLIGHT_HIGH_SIGNAL = "red-background"

RESULTS_LINK = "View results on ClinicalTrials.gov"

# Marks what has moved since the analyst last said they had read it.
UNREVIEWED = "🔔"


def render_field(row: dict) -> str:
    """One marked-up profile row, as the markdown the page renders.

    Kept here rather than in the page so what a highlight looks like can be
    tested without running Streamlit. Dates are shown as they are: the direction
    of a move is the intelligence, and no arithmetic is done on it.
    """
    name = label(row["field"])

    if row["field"] == "resultsUrl" and row["value"]:
        value = f"[{RESULTS_LINK}]({row['value']})"
    else:
        value = show(row["value"])

    if not row["changed"]:
        return f"**{name}**  \n{value}"

    badge = f" · {SYNTHETIC}" if row["synthetic"] else ""
    heading = (
        f"#### :{HIGHLIGHT_HIGH_SIGNAL}[{name}]"
        if row["high_signal"]
        else f":{HIGHLIGHT}[**{name}**]"
    )
    return f"{heading}{badge}  \n{value}  \n_Previously {show(row['previous'])}_"


# --- the watchlist table
#
# One line per trial, so every cell is a single short string. Pure functions
# over a row from monitor.watchlist, kept here so the table's wording can be
# tested without running Streamlit.

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
