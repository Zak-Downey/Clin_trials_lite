"""Pure formatting helpers shared by the view layer.

Kept out of the Streamlit page so they can be tested without running the app.
"""

from __future__ import annotations

import re

EMPTY = "—"

# Shown against anything the simulator caused, so nobody in a demo mistakes
# fabricated data for the registry's.
SYNTHETIC = "🧪 SYNTHETIC"


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
