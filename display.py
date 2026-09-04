"""Pure formatting helpers shared by the view layer.

Kept out of the Streamlit page so they can be tested without running the app.
"""

from __future__ import annotations

import re

EMPTY = "—"


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
